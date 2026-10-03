"""Tests for smart_auth.py.

No live authorization server needed for this module — these exercises
work directly on claims dicts, signed JWT strings, and token response
JSON. The RSA keypair below stands in for a real client's registered
keypair.
"""

import pathlib
import sys
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

sys.path.insert(0, str(pathlib.Path(__file__).parent))
import smart_auth  # noqa: E402

CLIENT_ID = "test-backend-client"
TOKEN_URL = "https://ehr.example.org/oauth/token"


@pytest.fixture(scope="module")
def keypair():
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private_key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def test_build_system_scope_joins_in_order():
    scope = smart_auth.build_system_scope(["Patient", "Observation"], access="read")
    assert scope == "system/Patient.read system/Observation.read"


def test_build_client_assertion_claims_shape():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    claims = smart_auth.build_client_assertion_claims(CLIENT_ID, TOKEN_URL, now)

    assert claims["iss"] == CLIENT_ID
    assert claims["sub"] == CLIENT_ID
    assert claims["aud"] == TOKEN_URL
    assert claims["iat"] == int(now.timestamp())
    assert claims["exp"] == int(now.timestamp()) + smart_auth.ASSERTION_LIFETIME_SECONDS
    assert isinstance(claims["jti"], str) and len(claims["jti"]) > 0


def test_build_client_assertion_claims_jti_is_unique_per_call():
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    claims_1 = smart_auth.build_client_assertion_claims(CLIENT_ID, TOKEN_URL, now)
    claims_2 = smart_auth.build_client_assertion_claims(CLIENT_ID, TOKEN_URL, now)
    assert claims_1["jti"] != claims_2["jti"]


def test_sign_and_verify_client_assertion_round_trips(keypair):
    private_pem, public_pem = keypair
    now = datetime.now(timezone.utc)
    claims = smart_auth.build_client_assertion_claims(CLIENT_ID, TOKEN_URL, now)

    token = smart_auth.sign_client_assertion(claims, private_pem, kid="key-1")
    verified = smart_auth.verify_client_assertion(token, public_pem, audience=TOKEN_URL)

    assert verified["iss"] == CLIENT_ID
    assert verified["jti"] == claims["jti"]
    assert jwt.get_unverified_header(token)["kid"] == "key-1"


def test_verify_client_assertion_rejects_wrong_audience(keypair):
    private_pem, public_pem = keypair
    now = datetime.now(timezone.utc)
    claims = smart_auth.build_client_assertion_claims(CLIENT_ID, TOKEN_URL, now)
    token = smart_auth.sign_client_assertion(claims, private_pem, kid="key-1")

    with pytest.raises(jwt.InvalidAudienceError):
        smart_auth.verify_client_assertion(token, public_pem, audience="https://not-the-token-url.example.org")


def test_verify_client_assertion_rejects_expired_token(keypair):
    private_pem, public_pem = keypair
    expired_now = datetime.now(timezone.utc) - timedelta(hours=1)
    claims = smart_auth.build_client_assertion_claims(CLIENT_ID, TOKEN_URL, expired_now)
    token = smart_auth.sign_client_assertion(claims, private_pem, kid="key-1")

    with pytest.raises(jwt.ExpiredSignatureError):
        smart_auth.verify_client_assertion(token, public_pem, audience=TOKEN_URL)


def test_build_token_request_body_shape():
    body = smart_auth.build_token_request_body("signed.jwt.token", "system/Patient.read")
    assert body == {
        "grant_type": "client_credentials",
        "client_assertion_type": smart_auth.CLIENT_ASSERTION_TYPE,
        "client_assertion": "signed.jwt.token",
        "scope": "system/Patient.read",
    }


def test_parse_token_response_returns_valid_response():
    response = {"access_token": "abc123", "expires_in": 300, "scope": "system/Patient.read"}
    assert smart_auth.parse_token_response(response) == response


def test_parse_token_response_raises_on_error():
    response = {"error": "invalid_client", "error_description": "unknown client_id"}
    with pytest.raises(RuntimeError):
        smart_auth.parse_token_response(response)


def test_parse_token_response_raises_on_missing_field():
    response = {"access_token": "abc123", "expires_in": 300}
    with pytest.raises(KeyError):
        smart_auth.parse_token_response(response)


def test_is_token_expired_false_when_fresh():
    issued_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    now = issued_at + timedelta(seconds=60)
    assert smart_auth.is_token_expired(issued_at, expires_in=300, now=now) is False


def test_is_token_expired_true_past_skew_window():
    issued_at = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    now = issued_at + timedelta(seconds=280)
    assert smart_auth.is_token_expired(issued_at, expires_in=300, now=now, skew_seconds=30) is True
