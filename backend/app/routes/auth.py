from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import timedelta

from app.database.db import get_db
from app.models.models import User, Cooperative
from app.schemas.auth import UserCreate, UserLogin, UserResponse, Token, SignupRequest, SignupResponse
from app.services.auth_service import get_password_hash, verify_password, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES

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

    new_coop = Cooperative(
        name=data.cooperative_name,
        location=data.location,
        description=description,
        currency="GHS",
    )
    db.add(new_coop)
    db.flush()  # get the ID without committing yet

    # 3. Create the admin user linked to that cooperative
    new_user = User(
        email=data.email,
        hashed_password=get_password_hash(data.password),
        role="admin",
        cooperative_id=new_coop.id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    db.refresh(new_coop)

    # 4. Issue JWT
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.email, "user_id": new_user.id, "cooperative_id": new_coop.id},
        expires_delta=access_token_expires,
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "cooperative_id": new_coop.id,
        "cooperative_name": new_coop.name,
    }


@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    hashed_password = get_password_hash(user_in.password)
    new_user = User(
        email=user_in.email,
        hashed_password=hashed_password,
        cooperative_id=user_in.cooperative_id,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user


@router.post("/login", response_model=Token)
def login(user_in: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == user_in.email).first()
    if not user or not verify_password(user_in.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email, "user_id": user.id, "cooperative_id": user.cooperative_id},
        expires_delta=access_token_expires,
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": UserResponse.model_validate(user),
    }
