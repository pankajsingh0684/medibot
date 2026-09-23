from datetime import datetime, timedelta, timezone

import jwt
import pytest

from medibot.auth import (
    create_access_token,
    decode_access_token,
    hash_password,
    verify_password,
)
from medibot.config import Settings
from medibot.models import Role


@pytest.fixture
def settings() -> Settings:
    return Settings(jwt_secret_key="a" * 32)


def test_password_hash_round_trip() -> None:
    hashed = hash_password("correct horse battery staple")

    assert hashed != "correct horse battery staple"
    assert verify_password("correct horse battery staple", hashed)
    assert not verify_password("wrong password", hashed)


def test_access_token_contains_authenticated_role(settings: Settings) -> None:
    token = create_access_token("dr.mehta", Role.DOCTOR, settings)

    token_data = decode_access_token(token, settings)

    assert token_data.username == "dr.mehta"
    assert token_data.role is Role.DOCTOR


def test_expired_token_is_rejected(settings: Settings) -> None:
    token = jwt.encode(
        {
            "sub": "nurse.priya",
            "role": Role.NURSE.value,
            "iat": datetime.now(timezone.utc) - timedelta(minutes=2),
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )

    with pytest.raises(Exception) as error:
        decode_access_token(token, settings)

    assert error.value.status_code == 401
