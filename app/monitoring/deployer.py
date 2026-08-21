import subprocess
import logging
import os
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DeployResult:
    success: bool
    message: str
    branch: str
    commit_sha: str = ""
    duration: float = 0.0


def _run_git(args: list, timeout: int = 60) -> tuple[int, str, str]:
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return 1, "", f"git command timed out after {timeout}s"
    except Exception as e:
        return 1, "", str(e)


def _get_current_branch() -> str:
    code, stdout, _ = _run_git(["rev-parse", "--abbrev-ref", "HEAD"])
    return stdout if code == 0 else "unknown"


def _get_latest_commit() -> str:
    code, stdout, _ = _run_git(["rev-parse", "--short", "HEAD"])
    return stdout if code == 0 else "unknown"


def _has_uncommitted_changes() -> bool:
    code, stdout, _ = _run_git(["status", "--porcelain"])
    return bool(stdout.strip()) if code == 0 else True


def _has_staged_changes() -> bool:
    code, stdout, _ = _run_git(["diff", "--cached", "--name-only"])
    return bool(stdout.strip()) if code == 0 else False


def check_deploy_safety() -> tuple[bool, str]:
    if _has_uncommitted_changes():
        return False, "Existem alterações não commitadas. Faça commit antes de deployar."

    branch = _get_current_branch()
    if branch not in ("main", "master"):
        return False, f"Branch atual é '{branch}'. Deploy permitido apenas em main/master."

    return True, "OK"


def deploy(message: str = "Auto-deploy: correção aprovada via Telegram") -> DeployResult:
    start = time.time()

    safe, msg = check_deploy_safety()
    if not safe:
        logger.warning("Deploy safety check failed: %s", msg)
        return DeployResult(success=False, message=msg, branch="unknown")

    branch = _get_current_branch()
    commit_sha = _get_latest_commit()

    if _has_staged_changes():
        code, _, err = _run_git(["commit", "-m", message])
        if code != 0:
            return DeployResult(
                success=False, message=f"Erro ao commitar: {err}",
                branch=branch, duration=time.time() - start,
            )

    code, stdout, err = _run_git(["push", "origin", branch], timeout=120)
    duration = time.time() - start

    if code == 0:
        logger.info("Deploy OK: pushed to %s in %.1fs", branch, duration)
        return DeployResult(
            success=True,
            message=f"Deploy realizado com sucesso!\nBranch: {branch}\nCommit: {commit_sha}\nTempo: {duration:.1f}s",
            branch=branch,
            commit_sha=commit_sha,
            duration=duration,
        )
    else:
        logger.warning("Deploy FAILED: %s", err)
        return DeployResult(
            success=False,
            message=f"Falha no push:\n{err}",
            branch=branch,
            duration=duration,
        )


def create_branch_and_commit(branch_name: str, message: str) -> DeployResult:
    start = time.time()

    code, _, err = _run_git(["checkout", "-b", branch_name])
    if code != 0:
        return DeployResult(
            success=False, message=f"Erro ao criar branch: {err}",
            branch=branch_name, duration=time.time() - start,
        )

    code, _, err = _run_git(["add", "-A"])
    if code != 0:
        return DeployResult(
            success=False, message=f"Erro ao adicionar arquivos: {err}",
            branch=branch_name, duration=time.time() - start,
        )

    code, _, err = _run_git(["commit", "-m", message])
    if code != 0:
        return DeployResult(
            success=False, message=f"Erro ao commitar: {err}",
            branch=branch_name, duration=time.time() - start,
        )

    return DeployResult(
        success=True,
        message=f"Branch '{branch_name}' criada e commit realizada.",
        branch=branch_name,
        commit_sha=_get_latest_commit(),
        duration=time.time() - start,
    )


def discard_changes() -> bool:
    code1, _, _ = _run_git(["checkout", "--", "."])
    code2, _, _ = _run_git(["clean", "-fd"])
    return code1 == 0 and code2 == 0
