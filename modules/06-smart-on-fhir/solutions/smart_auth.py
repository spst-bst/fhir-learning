"""Reference solution for Module 6. Don't peek until you've had a real go."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone

import jwt

CLIENT_ASSERTION_TYPE = "urn:ietf:params:oauth:client-assertion-type:jwt-bearer"
ASSERTION_LIFETIME_SECONDS = 300

# Set to False to quiet the debug dump below.
DEBUG = True


def _debug_print(label: str, **values) -> None:
    if not DEBUG:
        return
    print(f"\n--- {label} ---")
    for name, value in values.items():
        print(f"{name}: {json.dumps(value, default=str)}")


def build_system_scope(resource_types: list[str], access: str = "read") -> str:
    scope = " ".join(f"system/{rt}.{access}" for rt in resource_types)
    _debug_print("build_system_scope", resource_types=resource_types, scope=scope)
    return scope


def build_client_assertion_claims(client_id: str, token_url: str, now: datetime) -> dict:
    iat = int(now.timestamp())
    claims = {
        "iss": client_id,
        "sub": client_id,
        "aud": token_url,
        "jti": uuid.uuid4().hex,
        "iat": iat,
        "exp": iat + ASSERTION_LIFETIME_SECONDS,
    }
    _debug_print("build_client_assertion_claims", claims=claims)
    return claims


def sign_client_assertion(claims: dict, private_key_pem: str, kid: str) -> str:
    token = jwt.encode(claims, private_key_pem, algorithm="RS384", headers={"kid": kid})
    _debug_print("sign_client_assertion", kid=kid, token_preview=token[:24] + "...")
    return token


def verify_client_assertion(token: str, public_key_pem: str, audience: str) -> dict:
    claims = jwt.decode(token, public_key_pem, algorithms=["RS384"], audience=audience)
    _debug_print("verify_client_assertion", claims=claims)
    return claims


def build_token_request_body(client_assertion: str, scope: str) -> dict:
    body = {
        "grant_type": "client_credentials",
        "client_assertion_type": CLIENT_ASSERTION_TYPE,
        "client_assertion": client_assertion,
        "scope": scope,
    }
    _debug_print("build_token_request_body", scope=scope)
    return body


def parse_token_response(response_json: dict) -> dict:
    if "error" in response_json:
        description = response_json.get("error_description", response_json["error"])
        raise RuntimeError(f"token request failed: {description}")

    for required_key in ("access_token", "expires_in", "scope"):
        if required_key not in response_json:
            raise KeyError(required_key)

    _debug_print("parse_token_response", response=response_json)
    return response_json


def is_token_expired(issued_at: datetime, expires_in: int, now: datetime, skew_seconds: int = 30) -> bool:
    early_expiry = issued_at + timedelta(seconds=expires_in - skew_seconds)
    expired = now >= early_expiry
    _debug_print(
        "is_token_expired",
        issued_at=issued_at,
        expires_in=expires_in,
        now=now,
        expired=expired,
    )
    return expired
