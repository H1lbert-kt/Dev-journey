import os
import json
import hashlib
import logging
import threading
import time
import urllib.request
import urllib.parse
import urllib.error

logger = logging.getLogger(__name__)

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
IS_ENABLED = bool(TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID)

if not IS_ENABLED:
    logger.warning("Telegram notifications DISABLED: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
else:
    logger.info("Telegram notifications ENABLED (chat_id ends with ...%s)", TELEGRAM_CHAT_ID[-4:] if len(TELEGRAM_CHAT_ID) > 4 else "****")

_fingerprints: dict[str, float] = {}
_fingerprints_lock = threading.Lock()
_DEDUP_TTL = 60

_SENSITIVE_PATTERNS = (
    "password", "senha", "token", "secret", "authorization",
    "cookie", "session", "key", "credential", "api_key", "apikey",
)


def _fingerprint(error_type: str, endpoint: str, error_value: str) -> str:
    raw = f"{error_type}|{endpoint}|{error_value[:80]}"
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


def _is_duplicate(fp: str) -> bool:
    now = time.time()
    with _fingerprints_lock:
        expired = [k for k, v in _fingerprints.items() if now - v > _DEDUP_TTL]
        for k in expired:
            del _fingerprints[k]
        if fp in _fingerprints:
            return True
        _fingerprints[fp] = now
        return False


def _sanitize_url(url: str) -> str:
    if not url:
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        return ""


def _sanitize_value(text: str) -> str:
    if not text:
        return ""
    lower = text.lower()
    for pattern in _SENSITIVE_PATTERNS:
        if pattern in lower:
            return "[redacted - sensitive data in error message]"
    return text[:300]


def _send_telegram(text: str) -> bool:
    if not IS_ENABLED:
        logger.warning("Telegram send skipped: IS_ENABLED=False")
        return False
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }).encode()
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=10)
        resp_body = resp.read().decode()
        logger.info("Telegram message sent OK (status=%s)", resp.status)
        return True
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode()[:300]
        except Exception:
            pass
        logger.warning("Telegram API HTTP %s: %s", e.code, error_body)
        return False
    except urllib.error.URLError as e:
        logger.warning("Telegram API connection error: %s", e.reason)
        return False
    except Exception as e:
        logger.warning("Telegram notification failed: %s: %s", type(e).__name__, e)
        return False


def notify_error_async(error_type: str, error_value: str, endpoint: str = "",
                       level: str = "error", url: str = "",
                       environment: str = "unknown", timestamp: str = "",
                       frame_info: str = "") -> None:
    """Queue a Telegram notification in a background thread. Never blocks."""
    if not IS_ENABLED:
        return

    fp = _fingerprint(error_type, endpoint, error_value)
    if _is_duplicate(fp):
        return

    def _send():
        clean_value = _sanitize_value(error_value)
        clean_url = _sanitize_url(url)

        level_emoji = {"error": "🔴", "warning": "🟡", "fatal": "💀"}.get(level, "⚪")

        text = (
            f"{level_emoji} *DevJourney — {level.upper()}*\n\n"
            f"*{error_type}*\n"
            f"```\n{clean_value}\n```"
        )
        if frame_info:
            text += f"{frame_info}\n"
        if endpoint:
            text += f"*Endpoint:* `{endpoint}`\n"
        if clean_url:
            text += f"*URL:* {clean_url}\n"
        text += f"*Env:* {environment} | *Time:* {timestamp}"

        _send_telegram(text)

    t = threading.Thread(target=_send, daemon=True)
    t.start()
