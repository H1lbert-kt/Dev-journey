import hashlib
import secrets
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

SECRET_KEY = os.environ.get("DEVJOURNEY_SECRET_KEY", secrets.token_hex(32))
SESSION_EXPIRY_HOURS = 24

sessions: dict[str, dict] = {}


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    password_hash = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
    return f"{salt}:{password_hash}"


def verify_password(password: str, password_hash: str) -> bool:
    try:
        salt, stored_hash = password_hash.split(":")
        password_hash_check = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return password_hash_check == stored_hash
    except (ValueError, AttributeError):
        return False


def create_session(user_id: int) -> str:
    token = secrets.token_urlsafe(32)
    sessions[token] = {
        "user_id": user_id,
        "created_at": datetime.now(timezone.utc),
        "expires_at": datetime.now(timezone.utc) + timedelta(hours=SESSION_EXPIRY_HOURS),
    }
    return token


def get_session(token: Optional[str]) -> Optional[dict]:
    if not token:
        return None
    session = sessions.get(token)
    if not session:
        return None
    if datetime.now(timezone.utc) > session["expires_at"]:
        del sessions[token]
        return None
    return session


def delete_session(token: str):
    sessions.pop(token, None)


def sanitize_input(value: str) -> str:
    if not value:
        return value
    value = value.strip()
    value = value.replace("<script", "").replace("</script>", "")
    value = value.replace("javascript:", "")
    value = value.replace("onerror=", "").replace("onload=", "")
    return value
