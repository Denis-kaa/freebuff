"""Phase E tests for the replaceable MVP execution backend."""

import sys
import time

from app.execution import (
    ExecutionJob,
    ExecutionPolicy,
    ExecutionStatus,
    SandboxTier,
    TermuxSubprocessBackend,
)


def make_job(tmp_path: Path, code: str, env: dict[str, str] | None = None) -> ExecutionJob:
    script = tmp_path / "job.py"
    script.write_text(code, encoding="utf-8")
    return ExecutionJob(
        command=(sys.executable, str(script)),
        workspace=tmp_path,
        environment=env or {"PATH": "/usr/bin:/bin", "PYTHONNOUSERSITE": "1"},
    )


def test_completed_job_returns_output_and_exit_code(tmp_path: Path) -> None:
    result = TermuxSubprocessBackend().execute(
        make_job(tmp_path, "print('ok')"),
        ExecutionPolicy(cpu_seconds=None, address_space_bytes=None),
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert result.returncode == 0
    assert result.stdout.strip() == "ok"
    assert result.output_bytes > 0


def test_timeout_terminates_process_group(tmp_path: Path) -> None:
    result = TermuxSubprocessBackend().execute(
        make_job(
            tmp_path,
            "import subprocess\nimport sys\nimport time\n"
            "child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'])\n"
            "while True:\n    time.sleep(0.01)",
        ),
        ExecutionPolicy(timeout_seconds=0.1, cpu_seconds=None, address_space_bytes=None),
    )

    assert result.status is ExecutionStatus.TIMEOUT
    assert result.returncode is not None


def test_cpu_limit_normalizes_resource_exhaustion(tmp_path: Path) -> None:
    result = TermuxSubprocessBackend().execute(
        make_job(tmp_path, "while True:\n    pass"),
        ExecutionPolicy(timeout_seconds=4, cpu_seconds=1, address_space_bytes=None),
    )

    assert result.status is ExecutionStatus.RESOURCE_ERROR
    assert result.resource_error == "cpu_limit"


def test_output_limit_terminates_process(tmp_path: Path) -> None:
    result = TermuxSubprocessBackend().execute(
        make_job(tmp_path, "print('x' * 100000)"),
        ExecutionPolicy(
            max_output_bytes=128,
            cpu_seconds=None,
            address_space_bytes=None,
        ),
    )

    assert result.status is ExecutionStatus.OUTPUT_LIMIT
    assert result.output_bytes > 128


def test_environment_is_owned_by_job(tmp_path: Path) -> None:
    result = TermuxSubprocessBackend().execute(
        make_job(tmp_path, "import os\nprint(os.environ.get('SECRET', 'missing'))"),
        ExecutionPolicy(cpu_seconds=None, address_space_bytes=None),
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert result.stdout.strip() == "missing"


def test_working_directory_is_the_job_workspace(tmp_path: Path) -> None:
    result = TermuxSubprocessBackend().execute(
        make_job(tmp_path, ")\nprint(Path.cwd() == Path.cwd())"),
        ExecutionPolicy(cpu_seconds=None, address_space_bytes=None),
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert result.stdout.strip() == "True"


def test_address_space_policy_is_applied_to_direct_job(tmp_path: Path) -> None:
    limit = 16 * 1024 * 1024 * 1024
    result = TermuxSubprocessBackend().execute(
        make_job(
            tmp_path,
            "]\n"
            "for line in Path('/proc/self/limits').read_text().splitlines():\n"
            "    if line.startswith('Max address space'):\n"
            "        print(line)\n",
        ),
        ExecutionPolicy(
            timeout_seconds=3,
            cpu_seconds=None,
            address_space_bytes=limit,
        ),
    )

    assert result.status is ExecutionStatus.COMPLETED
    assert str(limit) in result.stdout


def test_policy_is_explicitly_mvp_only() -> None:
    policy = ExecutionPolicy()
    assert policy.sandbox_tier is SandboxTier.MVP_UNTRUSTED_SINGLE_USER
