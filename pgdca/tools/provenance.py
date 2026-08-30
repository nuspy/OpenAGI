"""Provenance digests and pinning for acquired capabilities (M10).

What was reviewed and approved is what runs: capability content is
digested at import time and re-verified on demand and after every
restart. A mismatch quarantines the capability (disabled + auditable
event) instead of silently executing changed code.
"""
from __future__ import annotations

import hashlib
from pathlib import Path


def digest_files(*paths: str | Path) -> str:
    """Order-stable sha256 over the named files' bytes (16 hex chars)."""
    h = hashlib.sha256()
    for p in paths:
        p = Path(p)
        h.update(str(p.name).encode())
        h.update(p.read_bytes())
    return h.hexdigest()[:16]


def skill_package_digest(package_path: str | Path) -> str:
    p = Path(package_path)
    return digest_files(p / "skill.json", p / "SKILL.md")


def pin_command(command: list[str]) -> dict | None:
    """Pin every argument of a server command that is an existing file
    (entry scripts, local binaries). A command with no file arguments
    (a bare PATH binary) cannot be pinned and says so honestly."""
    paths = [a for a in command if Path(a).is_file()]
    if not paths:
        return None
    return {"paths": [str(Path(a)) for a in paths],
            "digest": digest_files(*paths)}
