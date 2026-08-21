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


def _api_call(method: str, payload: dict) -> dict | None:
    if not IS_ENABLED:
        return None
    try:
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
        data = json.dumps(payload).encode()
        req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
        resp = urllib.request.urlopen(req, timeout=15)
        return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode()[:300]
        except Exception:
            pass
        logger.warning("Telegram API %s HTTP %s: %s", method, e.code, error_body)
        return None
    except Exception as e:
        logger.warning("Telegram API %s failed: %s: %s", method, type(e).__name__, e)
        return None


def send_message(text: str, chat_id: str = None, reply_markup: dict = None) -> dict | None:
    payload = {
        "chat_id": chat_id or TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return _api_call("sendMessage", payload)


def send_error_alert(error_type: str, error_value: str, endpoint: str = "",
                     method: str = "", environment: str = "unknown",
                     timestamp: str = "", frame_info: str = "",
                     approval_id: str = "", sentry_url: str = "") -> dict | None:
    clean_value = _sanitize_value(error_value)
    clean_url = _sanitize_url("")
    frame_clean = frame_info if frame_info else ""

    text = (
        f"🚨 *ERRO NO SERVIDOR*\n\n"
        f"DevJourney detectou um erro em produção.\n\n"
        f"*Erro:*\n```\n{error_type}: {clean_value}\n```\n"
    )
    if frame_clean:
        text += f"*Local:* `{frame_clean.strip()}`\n"
    if endpoint:
        text += f"*Endpoint:* `{method} {endpoint}`\n"
    text += f"*Ambiente:* {environment}\n"
    text += f"*Horário:* {timestamp}\n"
    if sentry_url:
        text += f"*Sentry:* [Ver evento]({sentry_url})\n"
    text += f"\nDeseja que o OpenCode analise e tente corrigir este erro?"

    reply_markup = None
    if approval_id:
        reply_markup = {
            "inline_keyboard": [[
                {"text": "✅ Sim, corrigir", "callback_data": f"fix:yes:{approval_id}"},
                {"text": "❌ Não corrigir", "callback_data": f"fix:no:{approval_id}"},
            ]]
        }

    return send_message(text, reply_markup=reply_markup)


def send_fix_result(approval_id: str, error_type: str, error_value: str,
                    files: list, summary: str, tests_passed: bool,
                    tests_output: str) -> dict | None:
    clean_value = _sanitize_value(error_value)
    files_text = "\n".join(f"  `{f}`" for f in files) if files else "  (nenhum)"
    test_emoji = "✅" if tests_passed else "❌"
    test_lines = tests_output.strip().split("\n")[-3:] if tests_output else []
    test_summary = "\n".join(test_lines)

    text = (
        f"🔧 *CORREÇÃO PREPARADA*\n\n"
        f"*Erro:*\n```\n{error_type}: {clean_value}\n```\n\n"
        f"*Causa encontrada:*\n{summary}\n\n"
        f"*Arquivos alterados:*\n{files_text}\n\n"
        f"*Testes:* {test_emoji}\n"
    )
    if test_summary:
        text += f"```\n{test_summary}\n```\n\n"

    if tests_passed:
        text += "Deseja fazer o deploy?"
        reply_markup = {
            "inline_keyboard": [[
                {"text": "🚀 DEPLOY", "callback_data": f"deploy:yes:{approval_id}"},
                {"text": "❌ CANCELAR", "callback_data": f"deploy:no:{approval_id}"},
            ]]
        }
    else:
        text += "❌ *CORREÇÃO NÃO APROVADA*\nNão realizar deploy."
        reply_markup = None

    return send_message(text, reply_markup=reply_markup)


def send_deploy_result(approval_id: str, success: bool, message: str) -> dict | None:
    if success:
        text = f"✅ *DEPLOY REALIZADO*\n\n{message}"
    else:
        text = f"❌ *DEPLOY FALHOU*\n\n{message}"
    return send_message(text)


def send_simple(text: str) -> dict | None:
    return send_message(text)


def notify_error_async(error_type: str, error_value: str, endpoint: str = "",
                       level: str = "error", url: str = "",
                       environment: str = "unknown", timestamp: str = "",
                       frame_info: str = "", approval_id: str = "",
                       sentry_url: str = "") -> None:
    if not IS_ENABLED:
        return

    fp = _fingerprint(error_type, endpoint, error_value)
    if _is_duplicate(fp):
        return

    def _send():
        send_error_alert(
            error_type=error_type,
            error_value=error_value,
            endpoint=endpoint,
            method=level,
            environment=environment,
            timestamp=timestamp,
            frame_info=frame_info,
            approval_id=approval_id,
            sentry_url=sentry_url,
        )

    t = threading.Thread(target=_send, daemon=True)
    t.start()
