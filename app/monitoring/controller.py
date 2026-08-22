import os
import sys
import logging
import signal

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from app.monitoring.config import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
from app.monitoring.telegram_bot import TelegramBot
from app.notifications.telegram import send_simple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("monitoring.controller")

bot = None


def _handle_callback(chat_id: int, data: str):
    logger.info("Callback ignored: %s", data)


def _handle_message(chat_id: int, text: str):
    if text == "/status":
        send_simple("📊 Sistema de monitoramento ativo.\nErros são reportados automaticamente.")
    elif text == "/help":
        send_simple(
            "🤖 *Comandos:*\n"
            "/status — Ver status do sistema\n"
            "/test — Enviar alerta de teste\n"
            "/help — Esta mensagem\n\n"
            "Erros em produção são enviados automaticamente para este chat."
        )
    elif text == "/test":
        _send_test_alert(chat_id)


def _send_test_alert(chat_id: int):
    import time
    from app.notifications.telegram import send_error_alert

    logger.info("Test alert triggered by chat_id=%d", chat_id)

    send_error_alert(
        error_type="TestError",
        error_value="Alerta de teste do sistema de monitoramento. Se você recebeu esta mensagem, o sistema está funcionando.",
        endpoint="/test",
        method="COMMAND",
        environment="test",
        timestamp=time.strftime("%Y-%m-%d %H:%M:%S"),
        frame_info="controller.py:_send_test_alert",
    )


def _setup_signal_handlers():
    def handler(signum, frame):
        logger.info("Received signal %d, shutting down...", signum)
        if bot:
            bot.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, handler)
    signal.signal(signal.SIGTERM, handler)


def main():
    global bot

    if not TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN not set. Cannot start controller.")
        sys.exit(1)
    if not TELEGRAM_CHAT_ID:
        logger.error("TELEGRAM_CHAT_ID not set. Cannot start controller.")
        sys.exit(1)

    _setup_signal_handlers()

    bot = TelegramBot(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID)
    bot.on_callback(_handle_callback)
    bot.on_message(_handle_message)

    logger.info("=" * 60)
    logger.info("DevJourney Monitoring Controller started")
    logger.info("Authorized chat_id: ...%s", TELEGRAM_CHAT_ID[-4:])
    logger.info("=" * 60)

    send_simple(
        "🤖 *DevJourney Controller iniciado*\n\n"
        "Sistema de monitoramento ativo.\n"
        "Erros em produção serão reportados automaticamente."
    )

    bot.poll(timeout=30)


if __name__ == "__main__":
    main()
