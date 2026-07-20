from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import AdminAuditLog, Cooperative, User
from app.schemas.auth import (
    SignupRequest,
    SignupResponse,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.services.auth_service import (
    ACCESS_TOKEN_EXPIRE_MINUTES,
    create_access_token,
    get_password_hash,
    require_roles,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=SignupResponse, status_code=201)
def signup(data: SignupRequest, db: Session = Depends(get_db)):
    """
    Combined onboarding: creates a new Cooperative and an admin User in one step.
    Returns a JWT access token immediately so the user is logged in right away.
    """
    # 1. Check email not already taken
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    # 2. Create the cooperative
    description = None
    if data.member_count:
        description = f"Approximate member count: {data.member_count}"

    import random
    while True:
        code = f"{random.randint(1000, 9999)}"
        if not db.query(Cooperative).filter(Cooperative.ussd_code == code).first():
            break

    new_coop = Cooperative(
        name=data.cooperative_name,
        location=data.location,
        description=description,
        currency="GHS",
        subscription_plan=data.subscription_plan,
        ussd_code=code,
    )

    import asyncio
    from app.services.moolre_service import MoolreService
    try:
        moolre_svc = MoolreService()
        moolre_result = asyncio.run(moolre_svc.create_account(account_name=data.cooperative_name))
        if moolre_result.get("success"):
            new_coop.moolre_account_number = moolre_result.get("account_number")
    except Exception as e:
        print(f"Warning: Failed to automatically create Moolre sub-wallet: {e}")

    db.add(new_coop)
    db.flush()  # get the ID without committing yet

    # 3. Create the admin user linked to that cooperative
    new_user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        role="admin",
        cooperative_id=new_coop.id,
        onboarding_role=data.onboarding_role,
    )
    db.add(new_user)
    db.flush()
    db.add(
        AdminAuditLog(
            cooperative_id=new_coop.id,
            actor_id=str(new_user.id),
            action="workspace.created",
            resource_type="cooperative",
            resource_id=str(new_coop.id),
            details=f"subscription_plan={new_coop.subscription_plan}",
        )
    )
    db.commit()
    db.refresh(new_user)
    db.refresh(new_coop)

    # 4. Issue JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": new_user.email,
            "user_id": new_user.id,
            "cooperative_id": new_coop.id,
            "role": new_user.role,
        },
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "cooperative_id": new_coop.id,
        "cooperative_name": new_coop.name,
        "subscription_plan": new_coop.subscription_plan,
        "onboarding_role": new_user.onboarding_role,
    }


@router.post("/register", response_model=UserResponse)
def register(
    user_in: UserCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        cooperative_id=current_user.cooperative_id,
        role=user_in.role,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.add(
        AdminAuditLog(
            cooperative_id=current_user.cooperative_id,
            actor_id=str(current_user.id),
            action="user.created",
            resource_type="user",
            resource_id=str(new_user.id),
            details=f"role={new_user.role}",
        )
    )
    db.commit()
    return new_user


@router.get("/users", response_model=list[UserResponse])
def list_users(
    cooperative_id: int | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    query = db.query(User)
    if current_user:
        query = query.filter(User.cooperative_id == current_user.cooperative_id)
    elif cooperative_id:
        query = query.filter(User.cooperative_id == cooperative_id)
    return query.order_by(User.email).all()


@router.patch("/users/{user_id}", response_model=UserResponse)
def update_user(
    user_id: int,
    body: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles("admin")),
):
    # Serialize all administrator-count decisions per cooperative.
    if current_user:
        coop_id = current_user.cooperative_id
    else:
        # If auth is disabled, allow editing any user. We must find their coop_id.
        target = db.query(User).filter(User.id == user_id).first()
        if not target:
            raise HTTPException(status_code=404, detail="User not found")
        coop_id = target.cooperative_id

    cooperative = (
        db.query(Cooperative)
        .filter(Cooperative.id == coop_id)
        .with_for_update()
        .first()
    )
    if not cooperative:
        raise HTTPException(status_code=404, detail="Cooperative not found")
    target = (
        db.query(User)
        .filter(
            User.id == user_id,
            User.cooperative_id == coop_id,
        )
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    if target.id == getattr(current_user, "id", None) and body.is_active is False:
        raise HTTPException(status_code=409, detail="You cannot deactivate your own account")
    removing_admin = target.role == "admin" and (
        body.role == "finance_officer" or body.is_active is False
    )
    if removing_admin:
        active_admins = (
            db.query(User)
            .filter(
                User.cooperative_id == coop_id,
                User.role == "admin",
                User.is_active.is_(True),
            )
            .count()
        )
        if active_admins <= 1:
            raise HTTPException(status_code=409, detail="At least one active administrator is required")
    if body.role is not None:
        target.role = body.role
    if body.is_active is not None:
        target.is_active = body.is_active
    db.add(
        AdminAuditLog(
            cooperative_id=coop_id,
            actor_id=str(current_user.id) if current_user else "system",
            action="user.updated",
            resource_type="user",
            resource_id=str(target.id),
            details=f"role={target.role};active={target.is_active}",
        )
    )
    db.commit()
    db.refresh(target)
    return target


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not user.is_active or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={
            "sub": user.email,
            "user_id": user.id,
            "cooperative_id": user.cooperative_id,
            "role": user.role,
        },
        expires_delta=access_token_expires,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user),
    }
