import json
import logging
import time
import urllib.request
import urllib.error
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class TelegramBot:
    def __init__(self, token: str, authorized_chat_id: str):
        self._token = token
        self._authorized_chat_id = str(authorized_chat_id)
        self._base_url = f"https://api.telegram.org/bot{token}"
        self._offset = 0
        self._running = False
        self._callback_handler: Optional[Callable] = None
        self._message_handler: Optional[Callable] = None

    def on_callback(self, handler: Callable):
        self._callback_handler = handler

    def on_message(self, handler: Callable):
        self._message_handler = handler

    def _api(self, method: str, data: dict = None) -> dict | None:
        try:
            url = f"{self._base_url}/{method}"
            payload = json.dumps(data or {}).encode()
            req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=30)
            result = json.loads(resp.read().decode())
            if not result.get("ok"):
                logger.warning("Telegram API %s returned ok=false: %s", method, result)
                return None
            return result
        except urllib.error.HTTPError as e:
            body = ""
            try:
                body = e.read().decode()[:300]
            except Exception:
                pass
            logger.warning("Telegram API %s HTTP %s: %s", method, e.code, body)
            return None
        except Exception as e:
            logger.warning("Telegram API %s error: %s", e)
            return None

    def send_message(self, chat_id: str, text: str, reply_markup: dict = None) -> dict | None:
        payload = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown",
            "disable_web_page_preview": True,
        }
        if reply_markup:
            payload["reply_markup"] = reply_markup
        return self._api("sendMessage", payload)

    def answer_callback(self, callback_id: str, text: str = "") -> bool:
        result = self._api("answerCallbackQuery", {
            "callback_query_id": callback_id,
            "text": text,
            "show_alert": False,
        })
        return result is not None

    def _is_authorized(self, chat_id: int) -> bool:
        return str(chat_id) == self._authorized_chat_id

    def _process_update(self, update: dict):
        if "callback_query" in update:
            cq = update["callback_query"]
            chat_id = cq["from"]["id"]
            callback_id = cq["id"]
            data = cq.get("data", "")

            if not self._is_authorized(chat_id):
                logger.warning("Unauthorized callback from chat_id=%d", chat_id)
                self.answer_callback(callback_id, "Não autorizado.")
                return

            logger.info("Callback from %d: %s", chat_id, data)
            self.answer_callback(callback_id)

            if self._callback_handler:
                try:
                    self._callback_handler(chat_id, data)
                except Exception as e:
                    logger.exception("Callback handler error: %s", e)

        elif "message" in update:
            msg = update["message"]
            chat_id = msg["from"]["id"]
            text = msg.get("text", "")

            if not self._is_authorized(chat_id):
                return

            if self._message_handler:
                try:
                    self._message_handler(chat_id, text)
                except Exception as e:
                    logger.exception("Message handler error: %s", e)

    def poll(self, timeout: int = 30):
        logger.info("Starting Telegram bot long-polling (timeout=%ds)", timeout)
        self._running = True

        while self._running:
            try:
                result = self._api("getUpdates", {
                    "offset": self._offset,
                    "timeout": timeout,
                    "allowed_updates": ["callback_query", "message"],
                })

                if result and result.get("result"):
                    for update in result["result"]:
                        self._offset = update["update_id"] + 1
                        self._process_update(update)

            except KeyboardInterrupt:
                logger.info("Bot polling stopped by user")
                break
            except Exception as e:
                logger.warning("Polling error: %s — retrying in 5s", e)
                time.sleep(5)

    def stop(self):
        self._running = False
        logger.info("Bot stopped")
