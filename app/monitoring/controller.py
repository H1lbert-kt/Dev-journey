import os
import sys
import logging
import signal
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from dotenv import load_dotenv
load_dotenv()

from app.monitoring.config import (
    TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID,
    APPROVAL_TTL_SECONDS, MAX_CONCURRENT_FIXES,
)
from app.monitoring.approval_manager import ApprovalManager
from app.monitoring.telegram_bot import TelegramBot
from app.monitoring.error_analyzer import analyze_error, format_analysis_for_telegram
from app.monitoring.test_runner import run_tests
from app.monitoring.deployer import deploy, check_deploy_safety, discard_changes
from app.notifications.telegram import send_fix_result, send_deploy_result, send_simple

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("monitoring.controller")

approval_manager = ApprovalManager(
    ttl_seconds=APPROVAL_TTL_SECONDS,
    max_concurrent=MAX_CONCURRENT_FIXES,
)

bot = None


def _handle_fix_approval(chat_id: int, approval_id: str):
    approval = approval_manager.approve(approval_id, chat_id)
    if not approval:
        send_simple("❌ Aprovação não encontrada ou já processada.")
        return

    if not approval_manager.can_fix():
        send_simple("⚠️ Já existe uma correção em andamento. Aguarde.")
        approval_manager.mark_fix_complete(
            approval_id, [], "", False, "Max concurrent fixes reached"
        )
        return

    logger.info("Starting fix analysis for approval %s (event %s)", approval_id, approval.event_id)
    send_simple("🔄 Analisando erro e preparando correção...")

    def _run_fix():
        try:
            approval_manager.mark_fixing(approval_id)

            analysis = analyze_error(
                error_type=approval.error_type,
                error_value=approval.error_value,
            )

            logger.info("Running test suite...")
            test_result = run_tests()

            files_changed = []
            if analysis.file_path:
                rel_path = os.path.relpath(analysis.file_path)
                files_changed.append(rel_path)

            summary = analysis.analysis
            if analysis.fix_suggestion:
                summary += f"\n{analysis.fix_suggestion}"

            approval_manager.mark_fix_complete(
                approval_id,
                files=files_changed,
                summary=summary,
                tests_passed=test_result.success,
                tests_output=test_result.output,
            )

            send_fix_result(
                approval_id=approval_id,
                error_type=approval.error_type,
                error_value=approval.error_value,
                files=files_changed,
                summary=summary,
                tests_passed=test_result.success,
                tests_output=test_result.output,
            )

            logger.info("Fix analysis complete for %s: %s", approval_id,
                        "PASS" if test_result.success else "FAIL")

        except Exception as e:
            logger.exception("Fix processing error: %s", e)
            approval_manager.mark_fix_complete(
                approval_id, [], f"Erro no processamento: {e}", False, str(e)
            )
            send_simple(f"❌ Erro ao processar correção: {e}")

    t = threading.Thread(target=_run_fix, daemon=True)
    t.start()


def _handle_fix_rejection(chat_id: int, approval_id: str):
    approval = approval_manager.reject(approval_id, chat_id)
    if approval:
        send_simple(f"ℹ️ Correção recusada para o evento {approval.event_id[:12]}...")
        logger.info("Fix rejected for approval %s", approval_id)
    else:
        send_simple("❌ Aprovação não encontrada.")


def _handle_deploy_approval(chat_id: int, approval_id: str):
    approval = approval_manager.approve_deploy(approval_id, chat_id)
    if not approval:
        send_simple("❌ Aprovação de deploy não encontrada.")
        return

    safe, msg = check_deploy_safety()
    if not safe:
        send_simple(f"❌ Deploy bloqueado: {msg}")
        approval_manager.mark_fix_complete(
            approval_id, approval.fix_files, approval.fix_summary,
            False, f"Deploy blocked: {msg}"
        )
        return

    logger.info("Deploy approved for approval %s", approval_id)
    send_simple("🚀 Iniciando deploy...")

    result = deploy(message=f"Auto-deploy: correção aprovada via Telegram\nEvent: {approval.event_id}")

    send_deploy_result(approval_id, result.success, result.message)

    if result.success:
        logger.info("Deploy successful: %s", result.message)
    else:
        logger.warning("Deploy failed: %s", result.message)


def _handle_deploy_rejection(chat_id: int, approval_id: str):
    approval = approval_manager.reject_deploy(approval_id, chat_id)
    if approval:
        discard_changes()
        send_simple("ℹ️ Deploy cancelado. Alterações descartadas.")
        logger.info("Deploy rejected for approval %s", approval_id)
    else:
        send_simple("❌ Aprovação de deploy não encontrada.")


def _handle_callback(chat_id: int, data: str):
    parts = data.split(":")
    if len(parts) != 3:
        logger.warning("Invalid callback data: %s", data)
        return

    action, response, approval_id = parts

    if action == "fix":
        existing = approval_manager.get_approval(approval_id)
        if not existing:
            approval = approval_manager.create_approval(
                event_id=approval_id,
                error_type="Unknown",
                error_value="Error details pending analysis",
                endpoint="unknown",
                method="UNKNOWN",
                environment="production",
                timestamp="",
                sentry_url="",
            )
            logger.info("Created approval %s from callback", approval_id)

        if response == "yes":
            _handle_fix_approval(chat_id, approval_id)
        elif response == "no":
            _handle_fix_rejection(chat_id, approval_id)

    elif action == "deploy":
        if response == "yes":
            _handle_deploy_approval(chat_id, approval_id)
        elif response == "no":
            _handle_deploy_rejection(chat_id, approval_id)

    else:
        logger.warning("Unknown callback action: %s", action)


def _handle_message(chat_id: int, text: str):
    if text == "/status":
        can_fix = approval_manager.can_fix()
        status = "Disponível" if can_fix else "Ocupado"
        send_simple(f"📊 Status: {status}\nCorreções ativas: {MAX_CONCURRENT_FIXES - (0 if can_fix else 1)}/{MAX_CONCURRENT_FIXES}")
    elif text == "/help":
        send_simple(
            "🤖 *Comandos:*\n"
            "/status — Ver status do sistema\n"
            "/help — Esta mensagem\n\n"
            "Use os botões inline para aprovar/rejeitar correções e deploys."
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
    logger.info("Approval TTL: %ds", APPROVAL_TTL_SECONDS)
    logger.info("Max concurrent fixes: %d", MAX_CONCURRENT_FIXES)
    logger.info("=" * 60)

    send_simple(
        "🤖 *DevJourney Controller iniciado*\n\n"
        "Sistema de monitoramento ativo.\n"
        "Erros em produção serão enviados aqui para aprovação."
    )

    bot.poll(timeout=30)


if __name__ == "__main__":
    main()
