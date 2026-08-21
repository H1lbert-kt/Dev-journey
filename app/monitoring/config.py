import os
import secrets

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SENTRY_DSN = os.environ.get("SENTRY_DSN", "")
SENTRY_AUTH_TOKEN = os.environ.get("SENTRY_AUTH_TOKEN", "")
SENTRY_ORG = os.environ.get("SENTRY_ORG", "")
SENTRY_PROJECT = os.environ.get("SENTRY_PROJECT", "devjourney")

APPROVAL_TTL_SECONDS = 3600
MAX_CONCURRENT_FIXES = 1
FIX_ID_PREFIX = "fix"
DEPLOY_ID_PREFIX = "deploy"

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REPO_DIR = BASE_DIR
TEST_COMMAND = ["python", "-m", "pytest", "tests/", "-q", "--tb=short"]
