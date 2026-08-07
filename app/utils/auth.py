import hashlib
import secrets
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

SECRET_KEY = os.environ.get("DEVJOURNEY_SECRET_KEY", secrets.token_hex(32))
SESSION_EXPIRY_HOURS = 24


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


def create_session(user_id: int, db) -> str:
    from app.models.user_session import UserSession

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=SESSION_EXPIRY_HOURS)

    session = UserSession(
        token=token,
        user_id=user_id,
        expires_at=expires_at,
    )
    db.add(session)
    db.commit()
    return token


def get_session(token: Optional[str], db) -> Optional[dict]:
    if not token:
        return None

    from app.models.user_session import UserSession

    session = db.query(UserSession).filter(UserSession.token == token).first()
    if not session:
        return None

    if datetime.now(timezone.utc) > session.expires_at:
        db.delete(session)
        db.commit()
        return None

    return {"user_id": session.user_id, "token": session.token}


def delete_session(token: str, db):
    from app.models.user_session import UserSession

    session = db.query(UserSession).filter(UserSession.token == token).first()
    if session:
        db.delete(session)
        db.commit()


def delete_session_token(token: str):
    from app.database.connection import SessionLocal
    db = SessionLocal()
    try:
        delete_session(token, db)
    finally:
        db.close()


def sanitize_input(value: str) -> str:
    if not value:
        return value
    value = value.strip()
    value = value.replace("<script", "").replace("</script>", "")
    value = value.replace("javascript:", "")
    value = value.replace("onerror=", "").replace("onload=", "")
    return value
