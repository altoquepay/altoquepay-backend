from datetime import UTC, datetime, timedelta
from typing import Any

import jwt

from app.iam.application.ports.token_service import TokenClaims, TokenService
from app.shared.interfaces.rest.security import JWT_ALGORITHM


class JwtTokenService(TokenService):
    """Signs the claims that shared/interfaces/rest/security.py validates."""

    def __init__(self, secret: str, expire_minutes: int) -> None:
        self._secret = secret
        self._lifetime = timedelta(minutes=expire_minutes)

    def issue(self, claims: TokenClaims) -> str:
        now = datetime.now(UTC)
        payload: dict[str, Any] = {
            # PyJWT requires sub to be a string.
            "sub": str(claims.user_id),
            "role": claims.role.value,
            "must_change_password": claims.must_change_password,
            "iat": now,
            "exp": now + self._lifetime,
        }
        if claims.store_id is not None:
            payload["store_id"] = claims.store_id
        if claims.customer_id is not None:
            payload["customer_id"] = claims.customer_id
        return jwt.encode(payload, self._secret, algorithm=JWT_ALGORITHM)
