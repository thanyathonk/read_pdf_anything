"""Shared FastAPI dependencies - avoids code duplication across routers."""

from typing import Optional
from fastapi import Header
from app.services.auth_service import auth_service


def get_user_id_from_token(
    authorization: Optional[str] = Header(None),
) -> Optional[str]:
    """Extract user ID from Authorization Bearer token. Returns None for guests."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        token = authorization.split(" ")[1]
        payload = auth_service.decode_token(token)
        return payload.get("sub") if payload else None
    except Exception:
        return None
