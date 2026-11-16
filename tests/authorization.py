"""Builds JWT headers for API tests, until the iam context can issue real tokens."""

from datetime import UTC, datetime, timedelta

import jwt

from app.shared.infrastructure.config import get_settings


def authorization(secret: str | None = None, **claim_overrides) -> dict[str, str]:
    """Build the header of a valid store admin token, changed by the given claims."""
    claims = {
        "sub": "7",
        "role": "STORE_ADMIN",
        "store_id": 3,
        "must_change_password": False,
        "exp": datetime.now(UTC) + timedelta(minutes=5),
        **claim_overrides,
    }
    claims = {name: value for name, value in claims.items() if value is not None}
    token = jwt.encode(claims, secret or get_settings().jwt_secret, algorithm="HS256")
    return {"Authorization": f"Bearer {token}"}
