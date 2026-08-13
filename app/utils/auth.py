import hashlib
import hmac
import secrets
import os
import logging
from datetime import datetime, timedelta
from typing import Optional

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError, InvalidHashError

logger = logging.getLogger(__name__)

SECRET_KEY = os.environ.get("SECRET_KEY", secrets.token_hex(32))
SESSION_EXPIRY_HOURS = 24

_ph = PasswordHasher(
    time_cost=3,
    memory_cost=65536,
    parallelism=4,
    hash_len=32,
    salt_len=16,
)


def hash_password(password: str) -> str:
    return _ph.hash(password)


def _is_argon2(hash_str: str) -> bool:
    return hash_str.startswith("$argon2")


def _verify_sha256_legacy(password: str, stored: str) -> bool:
    try:
        salt, expected = stored.split(":")
        computed = hashlib.sha256(f"{salt}{password}".encode()).hexdigest()
        return hmac.compare_digest(computed, expected)
    except (ValueError, AttributeError):
        return False


def verify_password(password: str, password_hash: str, user_id: int = None, db=None) -> bool:
    if _is_argon2(password_hash):
        try:
            _ph.verify(password_hash, password)
            return True
        except (VerifyMismatchError, VerificationError):
            return False

    if _verify_sha256_legacy(password, password_hash):
        if user_id is not None and db is not None:
            _rehash_password(password, user_id, db)
        return True

    return False


def _rehash_password(password: str, user_id: int, db) -> None:
    try:
        from app.models.user import User
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            user.password_hash = hash_password(password)
            db.commit()
            logger.info(f"Rehashed password for user {user_id} to argon2")
    except Exception as e:
        logger.warning(f"Failed to rehash password for user {user_id}: {e}")
        try:
            db.rollback()
        except Exception:
            pass


def create_session(user_id: int, db) -> str:
    from app.models.user_session import UserSession

    token = secrets.token_urlsafe(32)
    expires_at = datetime.now() + timedelta(hours=SESSION_EXPIRY_HOURS)

    session = UserSession(
        token=token,
        user_id=user_id,
        expires_at=expires_at,
    )
    db.add(session)
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    return token


def get_session(token: Optional[str], db) -> Optional[dict]:
    if not token:
        return None

    from app.models.user_session import UserSession

    session = db.query(UserSession).filter(UserSession.token == token).first()
    if not session:
        return None

    if datetime.now() > session.expires_at:
        db.delete(session)
        try:
            db.commit()
        except Exception:
            db.rollback()
        return None

    return {"user_id": session.user_id, "token": session.token}


def delete_session(token: str, db):
    from app.models.user_session import UserSession

    session = db.query(UserSession).filter(UserSession.token == token).first()
    if session:
        db.delete(session)
        try:
            db.commit()
        except Exception:
            db.rollback()


def sanitize_input(value: str) -> str:
    if not value:
        return value
    value = value.strip()
    value = value.replace("<", "&lt;").replace(">", "&gt;")
    value = value.replace('"', "&quot;").replace("'", "&#x27;")
    return value
