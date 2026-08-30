"""Tool registry: every capability is a port with a declared risk class.

Newly acquired tools enter at the most restrictive plausible class and
must pass conformance before use (spec: Tool Graph, acquisition
security). Phase 0 registers local toy adapters; MCP servers and skill
packages plug into this same registry in a later slice.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Protocol


@dataclass
class ToolResult:
    status: str                 # "ok" | "failed"
    observation: dict = field(default_factory=dict)
    error: str | None = None


class ToolPort(Protocol):
    def __call__(self, params: dict) -> ToolResult: ...


@dataclass
class ToolSpec:
    name: str
    risk_class: str
    description: str = ""
    provenance: str = "builtin"
    enabled: bool = True
    description_trust: str = "trusted"   # imported descriptions are "untrusted" data


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, tuple[ToolSpec, Callable[[dict], ToolResult]]] = {}

    def register(self, spec: ToolSpec, fn: Callable[[dict], ToolResult]) -> None:
        problems = conformance_check(fn)
        if problems:
            raise ValueError(f"tool '{spec.name}' failed conformance: {problems}")
        self._tools[spec.name] = (spec, fn)

    def spec(self, name: str) -> ToolSpec:
        return self._tools[name][0]

    def specs(self) -> list[ToolSpec]:
        return [self._tools[n][0] for n in sorted(self._tools)]

    def names(self, enabled_only: bool = True) -> list[str]:
        return sorted(n for n, (s, _) in self._tools.items()
                      if s.enabled or not enabled_only)

    def set_enabled(self, name: str, enabled: bool) -> None:
        if name in self._tools:
            self._tools[name][0].enabled = enabled

    def execute(self, name: str, params: dict) -> ToolResult:
        if name not in self._tools:
            return ToolResult(status="failed", error=f"unknown tool '{name}'")
        spec, fn = self._tools[name]
        if not spec.enabled:
            return ToolResult(status="failed",
                              error=f"tool '{name}' is disabled pending human approval")
        try:
            return fn(params)
        except Exception as exc:  # noqa: BLE001 - failures are data, not crashes
            return ToolResult(status="failed", error=repr(exc))


def conformance_check(fn: Callable[[dict], ToolResult]) -> list[str]:
    """A tool adapter must reject/absorb garbage input without raising
    and must return a ToolResult."""
    try:
        out = fn({"__conformance__": True})
    except Exception as exc:  # noqa: BLE001
        return [f"raised on conformance probe: {exc!r}"]
    if not isinstance(out, ToolResult):
        return ["did not return a ToolResult"]
    return []
