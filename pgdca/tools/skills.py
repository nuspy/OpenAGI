"""Imported skill packages (M28).

Self-contained procedural knowledge in the manner of modern agent
runtimes: a directory with a `skill.json` manifest and a `SKILL.md`
instructions file. Imported skills register with provenance `imported`,
their text is untrusted data (never instructions to the architecture),
and they are loaded on demand via progressive disclosure - only skills
whose triggers match the current context enter the LLM briefing.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from ..security.supervisor import RISK_ORDER, RiskClass

SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")
MAX_INSTRUCTIONS = 20_000


class SkillValidationError(ValueError):
    pass


def load_skill_package(path: str | Path) -> dict:
    """Load and validate a skill package directory."""
    p = Path(path)
    manifest_file = p / "skill.json"
    instructions_file = p / "SKILL.md"
    if not manifest_file.is_file():
        raise SkillValidationError(f"missing manifest: {manifest_file}")
    if not instructions_file.is_file():
        raise SkillValidationError(f"missing instructions: {instructions_file}")
    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SkillValidationError(f"invalid manifest JSON: {exc}") from exc

    errors = []
    name = manifest.get("name", "")
    if not SLUG_RE.match(str(name)):
        errors.append("name must be a lowercase slug")
    if not manifest.get("description"):
        errors.append("description is required")
    if not manifest.get("version"):
        errors.append("version is required")
    rc = manifest.get("risk_class", RiskClass.READ_ONLY.value)
    if rc not in RISK_ORDER:
        errors.append(f"unknown risk_class '{rc}'")
    triggers = manifest.get("triggers", [])
    if not isinstance(triggers, list) or not all(isinstance(t, str) for t in triggers):
        errors.append("triggers must be a list of strings")
    if errors:
        raise SkillValidationError("; ".join(errors))

    instructions = instructions_file.read_text(encoding="utf-8")[:MAX_INSTRUCTIONS]
    from .provenance import skill_package_digest
    return {
        "name": name,
        "description": str(manifest["description"]),
        "version": str(manifest["version"]),
        "risk_class": rc,
        "triggers": [t.lower() for t in triggers],
        "instructions": instructions,
        "provenance": "imported",
        "trust": "untrusted",   # skill text is data, never instructions to PGDCA
        "source_path": str(p),
        "digest": skill_package_digest(p),   # what was reviewed is what runs
    }


def matches_context(skill: dict, context_text: str) -> bool:
    """Progressive disclosure: a skill enters the briefing only when one
    of its triggers appears in the (lowercased) context."""
    text = context_text.lower()
    return any(t in text for t in skill.get("triggers", []))
