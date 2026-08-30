"""Sandbox-first execution for acquired capabilities (M10).

Imported tools and MCP server processes run inside a restricted
subprocess: resource limits (CPU, address space, file size), a
whitelisted environment (credentials and session variables never leak
into acquired code), an isolated working directory and a wall-clock
kill. This is the portable, dependency-free layer; OS-level network
isolation (bubblewrap, nsjail, containers) belongs to local deployment
and slots in behind this same profile without touching callers.
"""
from __future__ import annotations

import os
import shutil
import signal
import subprocess
import tempfile
import time
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_ALLOW_ENV = ("PATH", "LANG", "LC_ALL", "TZ", "PYTHONHASHSEED")


@dataclass
class SandboxProfile:
    cpu_seconds: int = 10
    memory_bytes: int = 512 * 1024 * 1024
    file_size_bytes: int = 16 * 1024 * 1024
    wall_seconds: float = 15.0
    allow_env: tuple = DEFAULT_ALLOW_ENV
    extra_env: dict = field(default_factory=dict)
    workdir: str | None = None            # default: a fresh private tempdir


def _restricted_env(profile: SandboxProfile, home: str) -> dict:
    env = {k: os.environ[k] for k in profile.allow_env if k in os.environ}
    env.update(profile.extra_env)
    env["HOME"] = home
    env["PGDCA_SANDBOX"] = "1"
    return env


def _limiter(profile: SandboxProfile):
    def apply_limits():
        import resource
        resource.setrlimit(resource.RLIMIT_CPU,
                           (profile.cpu_seconds, profile.cpu_seconds + 1))
        resource.setrlimit(resource.RLIMIT_AS,
                           (profile.memory_bytes, profile.memory_bytes))
        resource.setrlimit(resource.RLIMIT_FSIZE,
                           (profile.file_size_bytes, profile.file_size_bytes))
    return apply_limits


def sandbox_popen(command: list[str], profile: SandboxProfile | None = None,
                  **popen_kwargs) -> subprocess.Popen:
    """Launch a process under the sandbox profile. Long-lived processes
    (MCP servers) use this directly; pipes and text mode pass through."""
    profile = profile or SandboxProfile()
    workdir = profile.workdir or tempfile.mkdtemp(prefix="pgdca-sbx-")
    # the child runs in an isolated cwd: resolve file arguments (entry
    # scripts, local binaries) against the caller's cwd before moving
    command = [str(Path(a).resolve()) if Path(a).is_file() else a
               for a in command]
    popen_kwargs.setdefault("cwd", workdir)
    popen_kwargs.setdefault("env", _restricted_env(profile, workdir))
    popen_kwargs.setdefault("start_new_session", True)
    popen_kwargs.setdefault("preexec_fn", _limiter(profile))
    proc = subprocess.Popen(command, **popen_kwargs)
    proc._pgdca_workdir = workdir  # type: ignore[attr-defined]
    return proc


def kill_sandboxed(proc: subprocess.Popen) -> None:
    """Terminate the whole process group, then clean the private workdir."""
    if proc.poll() is None:
        try:
            os.killpg(proc.pid, signal.SIGTERM)
            proc.wait(timeout=2)
        except Exception:  # noqa: BLE001
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except Exception:  # noqa: BLE001
                pass
    workdir = getattr(proc, "_pgdca_workdir", None)
    if workdir and workdir.startswith(tempfile.gettempdir()):
        shutil.rmtree(workdir, ignore_errors=True)


def run_sandboxed(command: list[str], profile: SandboxProfile | None = None,
                  input_text: str | None = None) -> dict:
    """Run a short-lived command to completion under the sandbox.
    Returns {"status": ok|failed|killed, "returncode", "stdout",
    "stderr", "elapsed"}; a wall-clock overrun kills the process group."""
    profile = profile or SandboxProfile()
    start = time.monotonic()
    proc = sandbox_popen(command, profile, stdin=subprocess.PIPE,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         text=True)
    try:
        out, err = proc.communicate(input=input_text,
                                    timeout=profile.wall_seconds)
        status = "ok" if proc.returncode == 0 else "failed"
    except subprocess.TimeoutExpired:
        kill_sandboxed(proc)
        out, err = "", f"killed: wall clock exceeded {profile.wall_seconds}s"
        status = "killed"
    finally:
        kill_sandboxed(proc)
    return {"status": status, "returncode": proc.returncode,
            "stdout": (out or "")[:65536], "stderr": (err or "")[:65536],
            "elapsed": round(time.monotonic() - start, 3)}
