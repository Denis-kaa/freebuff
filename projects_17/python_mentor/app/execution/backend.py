"""Termux subprocess backend for the Phase E MVP tier.

The backend provides process, filesystem workspace, timeout, output and RLIMIT
controls. It does not provide OS-level network isolation or public multi-user
security in the current Termux/proot environment.
"""

from __future__ import annotations

import os
source
import signal
import subprocess
import time
from abc import ABC, abstractmethod
from pathlib import Path

from app.execution.contract import (
    ExecutionJob,
    ExecutionPolicy,
    ExecutionResult,
    ExecutionStatus,
)


class ExecutionBackend(ABC):
    """Replaceable execution interface for Grader and future hardened runtimes."""

    @abstractmethod
    def execute(self, job: ExecutionJob, policy: ExecutionPolicy) -> ExecutionResult:
        raise NotImplementedError


class TermuxSubprocessBackend(ExecutionBackend):
    """Local subprocess backend; explicit ``mvp_untrusted_single_user`` tier."""

    def execute(self, job: ExecutionJob, policy: ExecutionPolicy) -> ExecutionResult:
        started = time.monotonic()
        output_path = job.workspace / ".execution-output"
        try:
            with output_path.open("wb") as output_file:
                process = subprocess.Popen(
                    list(job.command),
                    cwd=job.workspace,
                    env=dict(job.environment),
                    stdout=output_file,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                    preexec_fn=self._resource_limiter(policy),
                )
                status = self._wait(process, output_path, policy)
                if status is ExecutionStatus.COMPLETED and process.returncode in {
                    -signal.SIGXCPU,
                    -signal.SIGKILL,
                } and policy.cpu_seconds is not None:
                    status = ExecutionStatus.RESOURCE_ERROR
        except (OSError, ValueError) as exc:
            return ExecutionResult(
                status=ExecutionStatus.START_ERROR,
                returncode=None,
                stdout="",
                output_bytes=0,
                duration_seconds=time.monotonic() - started,
                resource_error=type(exc).__name__,
            )

        output_bytes = output_path.stat().st_size if output_path.exists() else 0
        stdout = output_path.read_bytes()[: policy.max_output_bytes + 1].decode(
            "utf-8", errors="replace"
        )
        if status is ExecutionStatus.COMPLETED and output_bytes > policy.max_output_bytes:
            status = ExecutionStatus.OUTPUT_LIMIT
        resource_error = "cpu_limit" if status is ExecutionStatus.RESOURCE_ERROR else None
        return ExecutionResult(
            status=status,
            returncode=process.returncode,
            stdout=stdout,
            output_bytes=output_bytes,
            duration_seconds=time.monotonic() - started,
            resource_error=resource_error,
        )

    @staticmethod
    def _resource_limiter(policy: ExecutionPolicy):
        def limit() -> None:
            if policy.cpu_seconds is not None:
                hard = max(policy.cpu_seconds, policy.cpu_seconds + 1)
                resource.setrlimit(resource.RLIMIT_CPU, (policy.cpu_seconds, hard))
            if policy.address_space_bytes is not None:
                _, current_hard = resource.getrlimit(resource.RLIMIT_AS)
                hard = (
                    min(current_hard, policy.address_space_bytes)
                    if current_hard != resource.RLIM_INFINITY
                    else policy.address_space_bytes
                )
                soft = min(policy.address_space_bytes, hard)
                resource.setrlimit(resource.RLIMIT_AS, (soft, hard))

        return limit

    @staticmethod
    def _wait(
        process: subprocess.Popen[bytes],
        output_path: Path,
        policy: ExecutionPolicy,
    ) -> ExecutionStatus:
        deadline = time.monotonic() + policy.timeout_seconds
        while process.poll() is None:
            if output_path.stat().st_size > policy.max_output_bytes:
                TermuxSubprocessBackend._terminate(process)
                return ExecutionStatus.OUTPUT_LIMIT
            if time.monotonic() >= deadline:
                TermuxSubprocessBackend._terminate(process)
                return ExecutionStatus.TIMEOUT
            time.sleep(0.01)
        process.wait()
        return ExecutionStatus.COMPLETED

    @staticmethod
    def _terminate(process: subprocess.Popen[bytes]) -> None:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except ProcessLookupError:
            return
        try:
            process.wait(timeout=0.5)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait()
