import pytest

from app.core.config import Settings

SAFE = dict(environment="production", jwt_secret="x" * 40, cookie_secure=True,
            site_url="https://qutncandy.com", otp_enabled=False)


def test_production_accepts_safe_settings():
    Settings(_env_file=None, **SAFE)


@pytest.mark.parametrize("override, message", [
    ({"jwt_secret": "change-me"}, "JWT_SECRET"),
    ({"jwt_secret": "short"}, "JWT_SECRET"),
    ({"cookie_secure": False}, "COOKIE_SECURE"),
    ({"site_url": "http://qutncandy.com"}, "SITE_URL"),
    ({"otp_enabled": True}, "OTP_ENABLED"),
])
def test_production_rejects_unsafe_settings(override, message):
    with pytest.raises(ValueError, match=message):
        Settings(_env_file=None, **{**SAFE, **override})


def test_development_allows_defaults():
    Settings(_env_file=None, environment="development", jwt_secret="change-me")
