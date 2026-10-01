"""Unit-тесты криптографии и JWT."""
import pytest
import jwt as pyjwt

from app.config import get_settings
from app.core.exceptions import AuthenticationError
from app.security import jwt_service
from app.security.passwords import hash_password, validate_password_policy, verify_password


def test_password_is_hashed_with_bcrypt_and_verifies():
    h = hash_password("Secret123")
    assert h.startswith("$2") and "Secret123" not in h
    assert verify_password("Secret123", h)
    assert not verify_password("secret123", h)


def test_same_password_gives_different_hashes_random_salt():
    assert hash_password("Secret123") != hash_password("Secret123")


@pytest.mark.parametrize("pwd", ["short1A", "alllowercase1", "ALLUPPERCASE1", "NoDigitsHere"])
def test_password_policy_rejects_weak(pwd):
    assert validate_password_policy(pwd) is not None


def test_password_policy_accepts_strong():
    assert validate_password_policy("Str0ngPass1") is None


def test_access_token_roundtrip_and_short_lifetime():
    token = jwt_service.create_access_token(5, "CLIENT")
    payload = jwt_service.decode_token(token, jwt_service.ACCESS)
    assert payload["sub"] == "5" and payload["role"] == "CLIENT"
    assert payload["exp"] - payload["iat"] <= 30 * 60  # access живёт не дольше 30 минут


def test_refresh_token_cannot_be_used_as_access():
    token, _jti, _exp = jwt_service.create_refresh_token(5)
    with pytest.raises(AuthenticationError):
        jwt_service.decode_token(token, jwt_service.ACCESS)


def test_tampered_token_rejected():
    token = jwt_service.create_access_token(5, "CLIENT")
    with pytest.raises(AuthenticationError):
        jwt_service.decode_token(token[:-2] + "xx", jwt_service.ACCESS)


def test_token_signed_with_other_key_rejected():
    forged = pyjwt.encode({"sub": "1", "role": "ADMIN", "type": "access"}, "x" * 40, algorithm="HS256")
    with pytest.raises(AuthenticationError):
        jwt_service.decode_token(forged, jwt_service.ACCESS)


def test_alg_none_token_rejected():
    forged = pyjwt.encode({"sub": "1", "type": "access"}, None, algorithm="none")
    with pytest.raises(AuthenticationError):
        jwt_service.decode_token(forged, jwt_service.ACCESS)
    assert get_settings().jwt_algorithm == "HS256"
