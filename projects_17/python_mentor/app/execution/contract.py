"""Execution contracts shared by Grader and future sandbox backends."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping


class SandboxTier(str, Enum):
    """Explicit security tier; MVP is local and not production hardened."""

    MVP_UNTRUSTED_SINGLE_USER = "mvp_untrusted_single_user"
    HARDENED = "hardened"


class ExecutionStatus(str, Enum):
    COMPLETED = "completed"
    TIMEOUT = "timeout"
    OUTPUT_LIMIT = "output_limit"
    START_ERROR = "start_error"
    RESOURCE_ERROR = "resource_error"


@dataclass(frozen=True)
class ExecutionJob:
    """A command and its copied workspace; no student code is imported here."""

    command: tuple[str, ...]
    workspace: Path
    environment: Mapping[str, str]

    def __post_init__(self) -> None:
        if not self.command:
            raise ValueError("execution command must not be empty")
        if not self.workspace.is_dir():
            raise ValueError("execution workspace must exist")


@dataclass(frozen=True)
class ExecutionPolicy:
    """MVP resource policy. Network isolation is intentionally not claimed."""

    timeout_seconds: float = 15.0
    max_output_bytes: int = 64 * 1024
    cpu_seconds: int | None = 5
    # pytest itself can exceed 512 MiB of virtual address space in Termux/proot.
    address_space_bytes: int | None = 1024 * 1024 * 1024
    sandbox_tier: SandboxTier = SandboxTier.MVP_UNTRUSTED_SINGLE_USER

    def __post_init__(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        if self.max_output_bytes <= 0:
            raise ValueError("max_output_bytes must be positive")
        if self.cpu_seconds is not None and self.cpu_seconds <= 0:
            raise ValueError("cpu_seconds must be positive")
        if self.address_space_bytes is not None and self.address_space_bytes <= 0:
            raise ValueError("address_space_bytes must be positive")
        if self.sandbox_tier is not SandboxTier.MVP_UNTRUSTED_SINGLE_USER:
            raise ValueError("hardened backend is not implemented")


@dataclass(frozen=True)
class ExecutionResult:
    """Technical process outcome, intentionally separate from grading."""

    status: ExecutionStatus
    returncode: int | None
    stdout: str
    output_bytes: int
    duration_seconds: float
    resource_error: str | None = None

    @property
    def completed(self) -> bool:
        return self.status is ExecutionStatus.COMPLETED
