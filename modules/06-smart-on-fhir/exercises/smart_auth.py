"""Module 6 exercise: SMART Backend Services auth (signed JWT client auth).

Works directly on claims dicts, signed JWT strings, and token response
JSON rather than a live authorization server — the local HAPI server
doesn't implement SMART, and a real one needs a registered client and a
public JWKS endpoint, which would make for a bad exercise loop. The RSA
keypair used in the tests is generated on the fly as a stand-in for a
real client's registered keypair.

Run the tests with:
    make test-06
"""

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
    """Build a space-separated SMART backend-services scope string.

    Backend services (no user) use the "system/" prefix, not "patient/"
    or "user/" — e.g. ["Patient", "Observation"] with access="read"
    becomes "system/Patient.read system/Observation.read", in the same
    order as the input list.

    TODO: implement.
    """
    raise NotImplementedError


def build_client_assertion_claims(client_id: str, token_url: str, now: datetime) -> dict:
    """Build the JWT claims for a backend-services client assertion.

    Required claims per the SMART Backend Services spec:
        iss: client_id (the client asserts its own identity)
        sub: client_id (same as iss, for this flow)
        aud: token_url (ties the assertion to one specific endpoint —
             without this, a captured assertion could be replayed
             against a different token endpoint)
        jti: a unique value per assertion (prevents replay of the exact
             same assertion) — use uuid.uuid4().hex
        iat: now, as a Unix timestamp (int)
        exp: iat + ASSERTION_LIFETIME_SECONDS — short-lived by design

    Hint: datetime.timestamp() gives you a float; int() it.

    TODO: implement.
    """
    raise NotImplementedError


def sign_client_assertion(claims: dict, private_key_pem: str, kid: str) -> str:
    """Sign the claims into a JWT using RS384, with `kid` in the header.

    `kid` (key id) tells the server which of the client's registered
    public keys to verify against — a client can rotate keys by
    publishing a new one under a new kid without invalidating the old
    one immediately.

    Hint: jwt.encode(claims, private_key_pem, algorithm="RS384",
    headers={"kid": kid}).

    TODO: implement.
    """
    raise NotImplementedError


def verify_client_assertion(token: str, public_key_pem: str, audience: str) -> dict:
    """Verify a signed assertion and return its claims.

    Hint: jwt.decode(token, public_key_pem, algorithms=["RS384"],
    audience=audience) — PyJWT checks the signature, `exp`, and that
    `aud` matches the audience you pass in, raising on any mismatch
    (let those exceptions propagate; don't catch them here).

    TODO: implement.
    """
    raise NotImplementedError


def build_token_request_body(client_assertion: str, scope: str) -> dict:
    """Build the form-encoded body (as a dict) for the token request.

    Required fields per the spec:
        grant_type: "client_credentials"
        client_assertion_type: CLIENT_ASSERTION_TYPE
        client_assertion: the signed JWT string
        scope: the requested scope string

    TODO: implement.
    """
    raise NotImplementedError


def parse_token_response(response_json: dict) -> dict:
    """Validate and return a token endpoint's response.

    If the response has an "error" key, the request failed — raise
    RuntimeError with a message built from "error" and (if present)
    "error_description".

    Otherwise, require "access_token", "expires_in", and "scope" to all
    be present — raise KeyError (name the missing key) if any are
    missing. Return response_json unchanged if it's valid.

    TODO: implement.
    """
    raise NotImplementedError


def is_token_expired(issued_at: datetime, expires_in: int, now: datetime, skew_seconds: int = 30) -> bool:
    """Return whether a cached access token should be treated as expired.

    Subtract skew_seconds from the token's actual lifetime before
    comparing — refresh a little early rather than risk a request firing
    with a token that expires mid-flight. True if `now` is at or past
    that early-expiry point.

    TODO: implement.
    """
    raise NotImplementedError
