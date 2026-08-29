"""Phase E execution boundary: MVP local subprocess backend."""

from app.execution.backend import ExecutionBackend, TermuxSubprocessBackend
from app.execution.contract import (
    ExecutionJob,
    ExecutionPolicy,
    ExecutionResult,
    ExecutionStatus,
    SandboxTier,
)

__all__ = [
    "ExecutionBackend",
    "ExecutionJob",
    "ExecutionPolicy",
    "ExecutionResult",
    "ExecutionStatus",
    "SandboxTier",
    "TermuxSubprocessBackend",
***REMOVED***
