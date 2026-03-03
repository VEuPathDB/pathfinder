"""Authentication, authorization, and rate limiting."""

from __future__ import annotations

import time
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends, Request
from fastapi.security import APIKeyCookie
from slowapi import Limiter
from slowapi.util import get_remote_address

from veupath_chatbot.platform.config import get_settings
from veupath_chatbot.platform.context import user_id_ctx
from veupath_chatbot.platform.errors import UnauthorizedError

# Cookie-based auth is the public contract. We still accept an Authorization header
# as a non-documented fallback (parsed from request.headers) to avoid breaking
# internal tooling, but OpenAPI should reflect cookies.
auth_cookie = APIKeyCookie(name="pathfinder-auth", auto_error=False)

# Rate limiter (slowapi). Import and attach to the FastAPI app where needed.
limiter = Limiter(key_func=get_remote_address)


async def get_optional_user(
    request: Request,
    cookie_token: Annotated[str | None, Depends(auth_cookie)] = None,
) -> UUID | None:
    """Get current user ID if authenticated (optional)."""
    token_header: str | None = str(cookie_token) if cookie_token else None

    # Undocumented fallback: allow Authorization header for local tools.
    if not token_header:
        token_header = request.headers.get("Authorization")

    if not token_header:
        return None

    try:
        scheme, _, token = token_header.partition(" ")
        if scheme.lower() == "bearer":
            if not token:
                return None
        else:
            token = token_header

        settings = get_settings()
        payload = jwt.decode(token, settings.api_secret_key, algorithms=["HS256"])
        user_id = UUID(payload["sub"])
        user_id_ctx.set(user_id)
        return user_id
    except jwt.InvalidTokenError, ValueError, KeyError:
        return None


async def get_current_user(
    user_id: Annotated[UUID | None, Depends(get_optional_user)],
) -> UUID:
    """Get current user ID (required)."""
    if user_id is None:
        raise UnauthorizedError(detail="Not authenticated")
    return user_id


def create_user_token(user_id: UUID, expires_in: int = 86400) -> str:
    """Create a signed JWT for the given user.

    :param user_id: User UUID.
    :param expires_in: Token expiry in seconds (default: 86400).
    """
    settings = get_settings()
    payload = {
        "sub": str(user_id),
        "exp": int(time.time()) + expires_in,
    }
    return jwt.encode(payload, settings.api_secret_key, algorithm="HS256")
