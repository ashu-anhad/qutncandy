from datetime import timedelta

from fastapi import APIRouter, BackgroundTasks, Cookie, HTTPException, Response, status
from sqlalchemy import select, update

from app.core.deps import CurrentUser, DbSession
from app.core import messaging
from app.core.config import settings
from app.core.errors import get_or_404
from app.core.security import create_token, decode_token, hash_password

from . import service
from .models import Address, User
from .schemas import (
    AddressIn,
    AddressOut,
    ForgotPasswordIn,
    GoogleIn,
    LoginIn,
    OtpSendIn,
    OtpVerifyIn,
    ProfileUpdate,
    ResetPasswordIn,
    SignupIn,
    TokenOut,
    UserOut,
)

router = APIRouter(prefix="/api", tags=["auth"])


@router.post("/auth/signup", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
def signup(payload: SignupIn, db: DbSession, response: Response):
    user = service.create_user(db, payload.name, payload.email, payload.password)
    return service.issue_tokens(user, response)


@router.post("/auth/login", response_model=TokenOut)
def login(payload: LoginIn, db: DbSession, response: Response):
    user = service.authenticate(db, payload.email, payload.password)
    return service.issue_tokens(user, response)


@router.get("/auth/providers")
def providers():
    """Which login methods the frontend should offer."""
    return {"google_client_id": settings.google_client_id or None, "phone_otp": settings.otp_enabled}


@router.post("/auth/google", response_model=TokenOut)
def google_login(payload: GoogleIn, db: DbSession, response: Response):
    if not settings.google_client_id:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Google sign-in isn't set up yet")
    claims = service.verify_google_token(payload.credential)
    if claims is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Google sign-in failed. Please try again.")
    return service.issue_tokens(service.login_with_google(db, claims), response)


@router.post("/auth/otp/send", status_code=status.HTTP_204_NO_CONTENT)
def otp_send(payload: OtpSendIn, db: DbSession, tasks: BackgroundTasks):
    if not settings.otp_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Phone login isn't available yet")
    phone = service.normalise_phone(payload.phone)
    code = service.send_otp(db, phone)
    tasks.add_task(messaging.send_sms, phone, f"{code} is your {settings.store_name} login code. Valid for 5 minutes.")


@router.post("/auth/otp/verify", response_model=TokenOut)
def otp_verify(payload: OtpVerifyIn, db: DbSession, response: Response):
    if not settings.otp_enabled:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, "Phone login isn't available yet")
    phone = service.normalise_phone(payload.phone)
    service.verify_otp(db, phone, payload.code)
    user = db.scalar(select(User).where(User.phone == phone))
    if user is None:
        if not payload.name:
            # Code is correct but kept, so the client can resend it with a name.
            raise HTTPException(status.HTTP_428_PRECONDITION_REQUIRED, "Tell us your name to create your account")
        user = User(name=payload.name.strip(), phone=phone)
        db.add(user)
    elif not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "This account is disabled")
    service.consume_otps(db, phone)
    db.commit()
    db.refresh(user)
    return service.issue_tokens(user, response)


@router.post("/auth/refresh", response_model=TokenOut)
def refresh(db: DbSession, response: Response, refresh_token: str | None = Cookie(default=None)):
    payload = decode_token(refresh_token, "refresh") if refresh_token else None
    user = db.get(User, int(payload["sub"])) if payload else None
    if user is None or not user.is_active or user.token_version != payload["ver"]:
        service.clear_tokens(response)
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Session expired")
    return service.issue_tokens(user, response)


@router.post("/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response):
    service.clear_tokens(response)


@router.post("/auth/logout-all", status_code=status.HTTP_204_NO_CONTENT)
def logout_all(user: CurrentUser, db: DbSession, response: Response):
    user.token_version += 1
    db.commit()
    service.clear_tokens(response)


@router.post("/auth/forgot-password", status_code=status.HTTP_204_NO_CONTENT)
def forgot_password(payload: ForgotPasswordIn, db: DbSession, tasks: BackgroundTasks):
    """Email a 30-minute reset link. Always succeeds so it can't be used to discover accounts."""
    user = service.find_by_email(db, payload.email)
    if user is None or not user.is_active:
        return
    token = create_token(user.id, user.token_version, "reset", timedelta(minutes=30))
    link = f"{settings.site_url}/reset-password?token={token}"
    tasks.add_task(
        messaging.send_email, user.email, f"Reset your {settings.store_name} password",
        f"Hi {user.name},\n\nUse this link to choose a new password (valid for 30 minutes):\n{link}\n\n"
        f"If you didn't ask for this, you can ignore this email.\n\n— {settings.store_name}",
    )


@router.post("/auth/reset-password", response_model=TokenOut)
def reset_password(payload: ResetPasswordIn, db: DbSession, response: Response):
    data = decode_token(payload.token, "reset")
    user = db.get(User, int(data["sub"])) if data else None
    if user is None or not user.is_active or user.token_version != data["ver"]:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "This reset link is invalid or has expired")
    user.password_hash = hash_password(payload.password)
    user.token_version += 1  # signs out every other session and makes this link single-use
    db.commit()
    return service.issue_tokens(user, response)


@router.get("/me", response_model=UserOut)
def me(user: CurrentUser):
    return user


@router.patch("/me", response_model=UserOut)
def update_me(payload: ProfileUpdate, user: CurrentUser, db: DbSession):
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.commit()
    db.refresh(user)
    return user


# ---- addresses

def _own_address(db, user: User, address_id: int) -> Address:
    address = get_or_404(db, Address, address_id, "Address")
    if address.user_id != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Address not found")
    return address


def _make_default(db, user: User, address: Address) -> None:
    db.execute(update(Address).where(Address.user_id == user.id, Address.id != address.id).values(is_default=False))
    address.is_default = True


def _user_addresses(db, user: User) -> list[Address]:
    return db.scalars(
        select(Address).where(Address.user_id == user.id).order_by(Address.is_default.desc(), Address.id.desc())
    ).all()


@router.get("/me/addresses", response_model=list[AddressOut])
def list_addresses(user: CurrentUser, db: DbSession):
    return _user_addresses(db, user)


@router.post("/me/addresses", response_model=AddressOut, status_code=status.HTTP_201_CREATED)
def create_address(payload: AddressIn, user: CurrentUser, db: DbSession):
    is_first = not _user_addresses(db, user)
    address = Address(user_id=user.id, **payload.model_dump())
    db.add(address)
    db.flush()
    if payload.is_default or is_first:
        _make_default(db, user, address)
    db.commit()
    db.refresh(address)
    return address


@router.put("/me/addresses/{address_id}", response_model=AddressOut)
def update_address(address_id: int, payload: AddressIn, user: CurrentUser, db: DbSession):
    address = _own_address(db, user, address_id)
    was_default = address.is_default
    for k, v in payload.model_dump().items():
        setattr(address, k, v)
    if payload.is_default or was_default:  # the default can only move, never vanish
        _make_default(db, user, address)
    db.commit()
    db.refresh(address)
    return address


@router.delete("/me/addresses/{address_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_address(address_id: int, user: CurrentUser, db: DbSession):
    address = _own_address(db, user, address_id)
    was_default = address.is_default
    db.delete(address)
    db.flush()
    remaining = _user_addresses(db, user)
    if was_default and remaining:
        _make_default(db, user, remaining[0])
    db.commit()
