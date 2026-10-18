import hashlib
import hmac
import re
import secrets
from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException, Response, status
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.errors import commit_or_409
from app.core.security import create_token, hash_password, verify_password

from .models import OtpCode, User
from .schemas import TokenOut, UserOut

REFRESH_COOKIE = "refresh_token"
REFRESH_COOKIE_PATH = "/api/auth"


def find_by_email(db: Session, email: str) -> User | None:
    return db.scalar(select(User).where(func.lower(User.email) == email.lower()))


def create_user(db: Session, name: str, email: str, password: str, role: str = "customer") -> User:
    user = User(name=name, email=email.lower(), password_hash=hash_password(password), role=role)
    db.add(user)
    commit_or_409(db, "An account with that email already exists")
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = find_by_email(db, email)
    if user is None or not user.is_active or not verify_password(password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return user


def issue_tokens(user: User, response: Response) -> TokenOut:
    """Single exit point for every login method: access token in the body, refresh token in a cookie."""
    access = create_token(user.id, user.token_version, "access", timedelta(minutes=settings.access_token_minutes))
    refresh_lifetime = timedelta(days=settings.refresh_token_days)
    refresh = create_token(user.id, user.token_version, "refresh", refresh_lifetime)
    response.set_cookie(
        REFRESH_COOKIE,
        refresh,
        max_age=int(refresh_lifetime.total_seconds()),
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )
    return TokenOut(access_token=access, user=UserOut.model_validate(user))


def clear_tokens(response: Response) -> None:
    response.delete_cookie(REFRESH_COOKIE, path=REFRESH_COOKIE_PATH)


# ---------------- Google sign-in

GOOGLE_TOKENINFO = "https://oauth2.googleapis.com/tokeninfo"


def verify_google_token(credential: str) -> dict | None:
    """Ask Google to validate the ID token; returns its claims if it was issued for our client ID."""
    try:
        res = httpx.get(GOOGLE_TOKENINFO, params={"id_token": credential}, timeout=10)
    except httpx.HTTPError:
        raise HTTPException(502, "Couldn't reach Google. Please try again.")
    if res.status_code != 200:
        return None
    claims = res.json()
    if claims.get("aud") != settings.google_client_id:
        return None
    if claims.get("iss") not in ("accounts.google.com", "https://accounts.google.com"):
        return None
    if str(claims.get("email_verified")).lower() != "true" or not claims.get("email"):
        return None
    return claims


def login_with_google(db: Session, claims: dict) -> User:
    """Find by Google ID, else link to the account with the same (Google-verified) email, else create one."""
    user = db.scalar(select(User).where(User.google_id == claims["sub"]))
    if user is None:
        user = find_by_email(db, claims["email"])
        if user is not None:
            user.google_id = claims["sub"]
        else:
            name = claims.get("name") or claims["email"].split("@")[0]
            user = User(name=name[:100], email=claims["email"].lower(), google_id=claims["sub"])
            db.add(user)
    db.flush()  # applies column defaults (is_active) to a newly created user
    if not user.is_active:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "This account is disabled")
    db.commit()
    db.refresh(user)
    return user


# ---------------- phone OTP

OTP_TTL = timedelta(minutes=5)
OTP_MAX_ATTEMPTS = 5
OTP_RESEND_AFTER = timedelta(seconds=30)
OTP_MAX_PER_HOUR = 5


def normalise_phone(raw: str) -> str:
    """Accept '+91 98765 43210', '098765…' etc.; return the 10-digit mobile number or raise 422."""
    digits = re.sub(r"\D", "", raw)
    if len(digits) == 12 and digits.startswith("91"):
        digits = digits[2:]
    elif len(digits) == 11 and digits.startswith("0"):
        digits = digits[1:]
    if not re.fullmatch(r"[6-9]\d{9}", digits):
        raise HTTPException(422, "Enter a valid 10-digit Indian mobile number")
    return digits


def _hash_code(phone: str, code: str) -> str:
    return hmac.new(settings.jwt_secret.encode(), f"{phone}:{code}".encode(), hashlib.sha256).hexdigest()


def send_otp(db: Session, phone: str) -> str:
    """Create and send a login code. Returns the code (callers must never expose it)."""
    now = datetime.now(timezone.utc)
    db.execute(delete(OtpCode).where(OtpCode.created_at < now - timedelta(days=1)))
    recent = db.scalars(
        select(OtpCode.created_at).where(OtpCode.phone == phone, OtpCode.created_at >= now - timedelta(hours=1))
        .order_by(OtpCode.created_at.desc())
    ).all()
    if recent and now - recent[0] < OTP_RESEND_AFTER:
        raise HTTPException(429, "Please wait 30 seconds before requesting another code")
    if len(recent) >= OTP_MAX_PER_HOUR:
        raise HTTPException(429, "Too many codes requested. Please try again in an hour.")
    code = f"{secrets.randbelow(10**6):06d}"
    db.add(OtpCode(phone=phone, code_hash=_hash_code(phone, code), expires_at=now + OTP_TTL))
    db.commit()
    return code


def verify_otp(db: Session, phone: str, code: str) -> None:
    """Raise unless `code` matches the latest live code; consumes all codes for the phone on success."""
    otp = db.scalar(
        select(OtpCode).where(OtpCode.phone == phone, OtpCode.expires_at > datetime.now(timezone.utc))
        .order_by(OtpCode.created_at.desc()).limit(1).with_for_update()
    )
    if otp is None:
        raise HTTPException(400, "This code has expired. Please request a new one.")
    if otp.attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(400, "Too many incorrect attempts. Please request a new code.")
    if not hmac.compare_digest(otp.code_hash, _hash_code(phone, code)):
        otp.attempts += 1
        db.commit()
        raise HTTPException(400, "That code isn't right. Please check and try again.")


def consume_otps(db: Session, phone: str) -> None:
    db.execute(delete(OtpCode).where(OtpCode.phone == phone))
