# Phase E — Execution Runtime v0.1

## Contract

```text
ExecutionJob + ExecutionPolicy
  -> ExecutionBackend
  -> ExecutionResult
```

The backend is replaceable. `TermuxSubprocessBackend` is the only implemented backend; a hardened backend is intentionally not implemented in this phase.

`ExecutionPolicy` exposes:

- wall-clock timeout;
- bounded combined stdout/stderr;
- `RLIMIT_CPU` when supported;
- `RLIMIT_AS` policy when supported;
- explicit `sandbox_tier = mvp_untrusted_single_user`.

The backend runs a process group in a temporary workspace and terminates the group on timeout or output overflow. The workspace owner is responsible for creating and cleaning the temporary directory; `TemporaryDirectory` is used by the Grader boundary. Eight hermetic tests cover completion, timeout/process-group cleanup, CPU resource exhaustion, output limits, environment ownership, workspace execution and direct-job address-space policy.

The pytest grader applies wall-clock, CPU and output limits. It intentionally leaves `RLIMIT_AS` unset for pytest bootstrap in the current proot environment: even a generous address-space cap can produce false bootstrap timeouts. Direct execution jobs can still opt into the address-space policy through `ExecutionPolicy`. The decision and revisit triggers are recorded in [`ADR-005`***REMOVED***(../decisions/ADR-005_rlimit_as_termux_proot_mvp_hardened_boundary.md).

## Security limitations

This is a local Termux/proot MVP for one user. It is not a production security boundary. The implementation does not claim OS-level network isolation, arbitrary filesystem isolation from the current user, user switching, namespaces, seccomp, Docker, or nsjail. `unshare --net` was previously observed not to isolate network in this environment.

A future hardened backend must implement the same interface and prove its own security properties before public or multi-user execution is considered. G-E closes the local MVP contract only; it does not close the hardened sandbox requirement.
