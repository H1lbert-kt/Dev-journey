import subprocess
import logging
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    passed: int
    failed: int
    errors: int
    total: int
    output: str
    duration: float
    success: bool

    @property
    def summary(self) -> str:
        status = "✅" if self.success else "❌"
        return f"{status} {self.passed}/{self.total} testes passaram ({self.duration:.1f}s)"


def run_tests(command: list = None, timeout: int = 300) -> TestResult:
    if command is None:
        command = ["python", "-m", "pytest", "tests/", "-q", "--tb=short"]

    logger.info("Running tests: %s", " ".join(command))
    start = time.time()

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=None,
        )
        duration = time.time() - start
        output = result.stdout + "\n" + result.stderr
        output = output.strip()

        passed = 0
        failed = 0
        errors = 0
        total = 0

        import re
        summary_match = re.search(r'(\d+) passed', output)
        if summary_match:
            passed = int(summary_match.group(1))

        fail_match = re.search(r'(\d+) failed', output)
        if fail_match:
            failed = int(fail_match.group(1))

        error_match = re.search(r'(\d+) error', output)
        if error_match:
            errors = int(error_match.group(1))

        total = passed + failed + errors
        if total == 0:
            pass_match = re.search(r'(\d+) test', output)
            if pass_match:
                total = int(pass_match.group(1))

        success = result.returncode == 0 and failed == 0 and errors == 0

        logger.info("Tests: %s (exit code=%d)", "PASSED" if success else "FAILED", result.returncode)
        return TestResult(
            passed=passed,
            failed=failed,
            errors=errors,
            total=total,
            output=output[-2000:] if len(output) > 2000 else output,
            duration=duration,
            success=success,
        )

    except subprocess.TimeoutExpired:
        duration = time.time() - start
        logger.warning("Tests timed out after %ds", timeout)
        return TestResult(
            passed=0, failed=0, errors=1, total=1,
            output=f"Tests timed out after {timeout}s",
            duration=duration, success=False,
        )
    except Exception as e:
        duration = time.time() - start
        logger.exception("Test runner error: %s", e)
        return TestResult(
            passed=0, failed=0, errors=1, total=1,
            output=f"Test runner error: {e}",
            duration=duration, success=False,
        )
