from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.db import get_db
from app.models.models import AdminAuditLog, Cooperative, PendingCheckout, User
from app.auth.roles import COOP_ROLES, ROLE_CAPABILITIES, ROLE_LABELS, SOLO_ROLES, Role
from app.services import subscription_lifecycle as lifecycle
from app.schemas.auth import (
    AcceptInviteRequest,
    CurrentUserResponse,
    InviteUserRequest,
    InviteUserResponse,
    LogoutRequest,
    PasswordChangeRequest,
    PasswordResetConfirm,
    PasswordResetRequest,
    PasswordResetRequestResponse,
    RefreshRequest,
    RoleCatalogue,
    SignupRequest,
    SignupResponse,
    Token,
    UserCreate,
    UserLogin,
    UserResponse,
    UserUpdate,
)
from app.services import staff_email_service
from app.services.providers.factory import get_email_provider
from app.services.auth_service import (
    generate_reset_or_invite_token,
    get_current_user,
    get_optional_user,
    get_password_change_user,
    get_password_hash,
    invite_token_valid,
    require_roles,
    reset_token_valid,
    revoke_refresh_token,
    revoke_user_refresh_tokens,
    rotate_refresh_token,
    session_response,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=SignupResponse, status_code=201)
async def signup(data: SignupRequest, db: Session = Depends(get_db)):
    """
    Combined onboarding: creates a new Cooperative and an admin User in one step.
    Returns a JWT access token immediately so the user is logged in right away.
    """
    # 1. Check email not already taken
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    resolved_plan = data.subscription_plan
    resolved_band = data.subscription_band
    resolved_org_type = data.organization_type
    resolved_name = data.cooperative_name
    resolved_location = data.location
    resolved_member_count = data.member_count
    resolved_role = data.onboarding_role
    subscription_status = "active"
    subscription_expires_at = None

    if data.checkout_ref:
        checkout = (
            db.query(PendingCheckout)
            .filter(PendingCheckout.reference == data.checkout_ref)
            .with_for_update()
            .first()
        )
        if not checkout:
            raise HTTPException(status_code=404, detail="Checkout not found")
        if checkout.status != PendingCheckout.STATUS_PAID:
            raise HTTPException(status_code=402, detail="Payment not confirmed for this checkout")
        resolved_plan = checkout.plan_key
        resolved_band = checkout.band
        resolved_org_type = checkout.organization_type or data.organization_type
        resolved_name = checkout.organisation or data.cooperative_name
        resolved_location = checkout.location or data.location
        resolved_member_count = checkout.member_count or data.member_count
        resolved_role = checkout.role or data.onboarding_role
    elif data.subscription_plan != "starter":
        raise HTTPException(
            status_code=400,
            detail="Paid plans require a completed checkout",
        )

    if resolved_plan != "starter":
        # Paid checkout: first billing period starts now.
        subscription_expires_at = datetime.utcnow() + timedelta(days=lifecycle.PERIOD_DAYS)
    else:
        # Free signup: time-boxed Growth trial, then the free tier.
        subscription_status = lifecycle.STATUS_TRIAL
        subscription_expires_at = datetime.utcnow() + timedelta(days=lifecycle.TRIAL_DAYS)

    # 2. Create the cooperative
    description = None
    if resolved_member_count:
        description = f"Approximate member count: {resolved_member_count}"

    import random
    while True:
        code = f"{random.randint(1000, 9999)}"
        if not db.query(Cooperative).filter(Cooperative.ussd_code == code).first():
            break

    new_coop = Cooperative(
        name=resolved_name,
        location=resolved_location,
        description=description,
        currency="GHS",
        subscription_plan=resolved_plan,
        subscription_band=resolved_band,
        organization_type=resolved_org_type,
        subscription_status=subscription_status,
        subscription_expires_at=subscription_expires_at,
        ussd_code=code,
    )

    from app.services.providers.factory import get_payment_provider
    try:
        moolre_svc = get_payment_provider()
        moolre_result = await moolre_svc.create_account(
            account_name=resolved_name
        )
        if moolre_result.get("success"):
            new_coop.wallet_account_id = moolre_result.get("account_number")
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
        onboarding_role=resolved_role,
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
    if data.checkout_ref:
        checkout.status = PendingCheckout.STATUS_CONSUMED
        checkout.consumed_at = datetime.utcnow()
        checkout.cooperative_id = new_coop.id
    db.commit()
    db.refresh(new_user)
    db.refresh(new_coop)

    # 4. Issue session (short-lived access token + rotating refresh token)
    session = session_response(db, new_user)
    db.commit()

    return {
        **session,
        "cooperative_id": new_coop.id,
        "cooperative_name": new_coop.name,
        "subscription_plan": new_coop.subscription_plan,
        "subscription_band": new_coop.subscription_band,
        "organization_type": new_coop.organization_type,
        "onboarding_role": new_user.onboarding_role,
        "password_change_required": False,
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
        must_change_password=True,
        onboarding_role=user_in.onboarding_role if hasattr(user_in, 'onboarding_role') else None,
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
        if body.is_active is False:
            revoke_user_refresh_tokens(db, target.id)
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

    session = session_response(db, user)
    db.commit()
    return {
        **session,
        "user": UserResponse.model_validate(user),
        "cooperative_name": user.cooperative.name if user.cooperative else None,
        "organization_type": user.cooperative.organization_type if user.cooperative else None,
        "password_change_required": user.must_change_password,
    }


@router.post("/refresh", response_model=Token)
def refresh_session(data: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a live refresh token for a new access token **and** a new
    refresh token (#248). The presented refresh token is revoked; replaying
    it revokes every session for that user."""
    user, new_refresh = rotate_refresh_token(db, data.refresh_token)
    session = session_response(db, user, refresh_token=new_refresh)
    return {
        **session,
        "user": UserResponse.model_validate(user),
        "cooperative_name": user.cooperative.name if user.cooperative else None,
        "organization_type": user.cooperative.organization_type if user.cooperative else None,
        "password_change_required": user.must_change_password,
    }


@router.post("/logout", status_code=204)
def logout(
    data: LogoutRequest | None = None,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_optional_user),
):
    """Revoke refresh tokens: the presented one, or every live token for the
    signed-in user when none is supplied. Access tokens simply expire.
    Public so an expired access token can still present the refresh token."""
    if data and data.refresh_token:
        revoke_refresh_token(db, data.refresh_token)
    elif current_user is not None:
        revoke_user_refresh_tokens(db, current_user.id)
    db.commit()
    return None


def _current_user_response(user: User) -> CurrentUserResponse:
    base = UserResponse.model_validate(user).model_dump()
    return CurrentUserResponse(
        **base,
        cooperative_name=user.cooperative.name if user.cooperative else None,
        organization_type=user.cooperative.organization_type if user.cooperative else None,
        password_change_required=bool(user.must_change_password),
    )


@router.get("/roles", response_model=RoleCatalogue)
def list_roles():
    """Public catalogue of staff roles: label, what each may mutate, and the
    organisation tracks (``cooperative`` / ``solo_farm``) it belongs to."""
    roles = []
    for role in Role:
        tracks = []
        if role.value in COOP_ROLES:
            tracks.append("cooperative")
        if role.value in SOLO_ROLES:
            tracks.append("solo_farm")
        roles.append(
            {
                "key": role.value,
                "label": ROLE_LABELS[role.value],
                "capabilities": ROLE_CAPABILITIES[role.value],
                "tracks": tracks,
            }
        )
    return {"roles": roles}


@router.get("/me", response_model=CurrentUserResponse)
def read_current_user(current_user: User | None = Depends(get_current_user)):
    """Return the signed-in user's profile, cooperative name and organization type.

    401 when unauthenticated or when auth is disabled (there is no user to
    describe); the frontend must not fall back to fabricated demo data.
    """
    if current_user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return _current_user_response(current_user)

@router.post("/password-reset-request", response_model=PasswordResetRequestResponse, status_code=200)
def password_reset_request(data: PasswordResetRequest, db: Session = Depends(get_db)):
    """Always 200 so the response cannot be used to enumerate accounts. The
    reset link is delivered through the configured ``EmailProvider``; with the
    interim ``log`` adapter it is written to the backend log (#248)."""
    channel = get_email_provider().channel
    delivered = channel != "log"
    user = db.query(User).filter(User.email == data.email).first()
    if user and user.is_active:
        user.reset_token = generate_reset_or_invite_token()
        user.reset_token_expires_at = datetime.utcnow() + timedelta(minutes=15)
        db.commit()
        result = staff_email_service.send_password_reset_email(
            to=user.email, token=user.reset_token, expires_at=user.reset_token_expires_at
        )
        delivered = bool(result["delivered"])
    if delivered:
        message = "If that account exists, a reset link has been emailed to it."
    else:
        message = (
            "If that account exists, a reset link has been generated. Email delivery is not "
            "configured on this server — ask an administrator to retrieve the link from the backend log."
        )
    return {"message": message, "channel": channel, "delivered": delivered}

@router.post("/password-reset-confirm", status_code=200)
def password_reset_confirm(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.reset_token == data.reset_token).first()
    if not user or not reset_token_valid(user):
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
    user.hashed_password = get_password_hash(data.new_password)
    user.reset_token = None
    user.reset_token_expires_at = None
    user.must_change_password = False
    revoke_user_refresh_tokens(db, user.id)
    db.commit()
    return {"message": "Password has been reset successfully."}


@router.post("/change-password", status_code=200)
def change_password(
    data: PasswordChangeRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(get_password_change_user),
):
    if current_user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    current_user.hashed_password = get_password_hash(data.new_password)
    current_user.must_change_password = False
    # Other devices holding refresh tokens must sign in again with the new password.
    revoke_user_refresh_tokens(db, current_user.id)
    db.flush()
    session = session_response(db, current_user)
    db.commit()
    return {**session, "message": "Password has been changed successfully."}


@router.post("/invite", response_model=InviteUserResponse, status_code=201)
def invite_user(
    data: InviteUserRequest,
    db: Session = Depends(get_db),
    current_user: User | None = Depends(require_roles("admin")),
):
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    token = generate_reset_or_invite_token()
    expires = datetime.utcnow() + timedelta(hours=72)
    new_user = User(
        email=data.email,
        hashed_password="",
        role=data.role,
        cooperative_id=current_user.cooperative_id,
        invite_token=token,
        invite_token_expires_at=expires,
        must_change_password=True,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    result = staff_email_service.send_invite_email(
        to=new_user.email,
        cooperative_name=current_user.cooperative.name if current_user.cooperative else None,
        role=new_user.role,
        token=token,
        expires_at=expires,
    )
    db.add(
        AdminAuditLog(
            cooperative_id=current_user.cooperative_id,
            actor_id=str(current_user.id),
            action="user.invited",
            resource_type="user",
            resource_id=str(new_user.id),
            details=f"role={new_user.role};email_channel={result['channel']};delivered={result['delivered']}",
        )
    )
    db.commit()
    body = UserResponse.model_validate(new_user).model_dump()
    body["delivery"] = {
        "channel": result["channel"],
        "delivered": result["delivered"],
        "message": result["message"],
        "expires_at": expires,
        # Only the inviting admin sees the link, and only when email could not deliver it.
        "invite_link": None if result["delivered"] else result["link"],
    }
    return body

@router.post("/accept-invite", status_code=200)
def accept_invite(data: AcceptInviteRequest, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.invite_token == data.invite_token).first()
    if not user or not invite_token_valid(user):
        raise HTTPException(status_code=400, detail="Invalid or expired invite token.")
    user.hashed_password = get_password_hash(data.password)
    user.invite_token = None
    user.invite_token_expires_at = None
    user.must_change_password = False
    db.commit()
    return {"message": "Account activated. You may now login."}
