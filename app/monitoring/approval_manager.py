import threading
import time
import secrets
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class Approval:
    id: str
    event_id: str
    error_type: str
    error_value: str
    endpoint: str
    method: str
    environment: str
    timestamp: str
    sentry_url: str
    approved_by: Optional[int] = None
    approved_at: Optional[float] = None
    status: str = "pending"
    created_at: float = field(default_factory=time.time)
    fix_files: list = field(default_factory=list)
    fix_summary: str = ""
    tests_passed: bool = False
    tests_output: str = ""


class ApprovalManager:
    def __init__(self, ttl_seconds: int = 3600, max_concurrent: int = 1):
        self._approvals: dict[str, Approval] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds
        self._max_concurrent = max_concurrent
        self._active_fixes = 0

    def create_approval(self, event_id: str, error_type: str, error_value: str,
                        endpoint: str, method: str, environment: str,
                        timestamp: str, sentry_url: str = "") -> Approval:
        with self._lock:
            self._cleanup_expired()
            approval_id = f"{secrets.token_hex(8)}"
            approval = Approval(
                id=approval_id,
                event_id=event_id,
                error_type=error_type,
                error_value=error_value,
                endpoint=endpoint,
                method=method,
                environment=environment,
                timestamp=timestamp,
                sentry_url=sentry_url,
            )
            self._approvals[approval_id] = approval
            logger.info("Created approval %s for event %s", approval_id, event_id)
            return approval

    def get_approval(self, approval_id: str) -> Optional[Approval]:
        with self._lock:
            self._cleanup_expired()
            return self._approvals.get(approval_id)

    def approve(self, approval_id: str, user_chat_id: int) -> Optional[Approval]:
        with self._lock:
            self._cleanup_expired()
            approval = self._approvals.get(approval_id)
            if not approval:
                logger.warning("Approval %s not found or expired", approval_id)
                return None
            if approval.status != "pending":
                logger.warning("Approval %s already %s", approval_id, approval.status)
                return None
            if self._active_fixes >= self._max_concurrent:
                logger.warning("Max concurrent fixes reached (%d)", self._max_concurrent)
                return None
            approval.status = "approved"
            approval.approved_by = user_chat_id
            approval.approved_at = time.time()
            self._active_fixes += 1
            logger.info("Approval %s approved by %d", approval_id, user_chat_id)
            return approval

    def reject(self, approval_id: str, user_chat_id: int) -> Optional[Approval]:
        with self._lock:
            approval = self._approvals.get(approval_id)
            if not approval:
                return None
            if approval.status != "pending":
                return None
            approval.status = "rejected"
            approval.approved_by = user_chat_id
            approval.approved_at = time.time()
            logger.info("Approval %s rejected by %d", approval_id, user_chat_id)
            return approval

    def mark_fixing(self, approval_id: str) -> bool:
        with self._lock:
            approval = self._approvals.get(approval_id)
            if not approval or approval.status != "approved":
                return False
            approval.status = "fixing"
            return True

    def mark_fix_complete(self, approval_id: str, files: list, summary: str,
                          tests_passed: bool, tests_output: str) -> Optional[Approval]:
        with self._lock:
            approval = self._approvals.get(approval_id)
            if not approval:
                return None
            approval.status = "fix_ready" if tests_passed else "fix_failed"
            approval.fix_files = files
            approval.fix_summary = summary
            approval.tests_passed = tests_passed
            approval.tests_output = tests_output
            self._active_fixes = max(0, self._active_fixes - 1)
            return approval

    def approve_deploy(self, approval_id: str, user_chat_id: int) -> Optional[Approval]:
        with self._lock:
            approval = self._approvals.get(approval_id)
            if not approval or approval.status != "fix_ready":
                return None
            approval.status = "deploy_approved"
            approval.approved_by = user_chat_id
            approval.approved_at = time.time()
            return approval

    def reject_deploy(self, approval_id: str, user_chat_id: int) -> Optional[Approval]:
        with self._lock:
            approval = self._approvals.get(approval_id)
            if not approval or approval.status != "fix_ready":
                return None
            approval.status = "deploy_rejected"
            approval.approved_by = user_chat_id
            return approval

    def can_fix(self) -> bool:
        with self._lock:
            return self._active_fixes < self._max_concurrent

    def _cleanup_expired(self):
        now = time.time()
        expired = [k for k, v in self._approvals.items()
                   if now - v.created_at > self._ttl and v.status in ("pending",)]
        for k in expired:
            del self._approvals[k]
        if expired:
            logger.info("Cleaned up %d expired approvals", len(expired))
