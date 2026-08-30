"""LLM gateway: the provider-agnostic port for generative cognition.

The gateway validates structured outputs against a versioned schema
with a bounded repair loop, logs every request/response as events for
deterministic replay, and keeps instructions structurally separated
from (untrusted) data. Adapters implement `LlmPort`; the user's own
provider library plugs in here as an adapter (ports & adapters).

Phase 0 ships the port, a deterministic mock adapter, and a replay
adapter. A production Anthropic adapter would use the official SDK
with a current model id (e.g. `claude-opus-5`); it is intentionally
not part of Phase 0.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Protocol

from ..config import Config
from ..events import Actor, Ev
from ..security.supervisor import RiskClass

SCHEMA_VERSION = "cognitive_response/1"


class LlmPort(Protocol):
    def generate(self, request: dict) -> dict: ...


@dataclass
class Hypothesis:
    action_name: str
    params: dict
    rationale: str = ""
    expected: dict = field(default_factory=dict)
    success_prob: float = 0.8
    confidence: float = 0.8
    risk_class: str = RiskClass.READ_ONLY.value
    derived_from: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


@dataclass
class CognitiveResponse:
    role: str
    summary: str
    hypotheses: list[Hypothesis]
    assumptions: list[str]
    risks: list[dict]
    missing_information: list[str]
    confidence: float


class GatewayError(RuntimeError):
    pass


def _digest(obj: dict) -> str:
    return hashlib.sha256(json.dumps(obj, sort_keys=True).encode()).hexdigest()[:16]


def validate_response(raw: dict) -> tuple[CognitiveResponse | None, list[str]]:
    errors: list[str] = []
    if not isinstance(raw, dict):
        return None, ["response is not an object"]
    if raw.get("schema") != SCHEMA_VERSION:
        errors.append(f"schema must be '{SCHEMA_VERSION}'")
    for key in ("role", "summary", "hypotheses"):
        if key not in raw:
            errors.append(f"missing field '{key}'")
    # risks feed conflict handling downstream, which reads them as objects;
    # a bare string here would crash the cycle instead of being repaired
    for i, r in enumerate(raw.get("risks", []) or []):
        if not isinstance(r, dict):
            errors.append(f"risk {i} must be an object")
    hyps: list[Hypothesis] = []
    for i, h in enumerate(raw.get("hypotheses", [])):
        if not isinstance(h, dict) or "action_name" not in h or "params" not in h:
            errors.append(f"hypothesis {i} must have action_name and params")
            continue
        sp = h.get("success_prob", 0.8)
        if not (0.0 <= float(sp) <= 1.0):
            errors.append(f"hypothesis {i} success_prob out of [0,1]")
            continue
        rc = h.get("risk_class", RiskClass.READ_ONLY.value)
        # an unknown risk class would crash the supervisor downstream; the
        # repair loop tells the model which values exist instead
        if rc not in {r.value for r in RiskClass}:
            errors.append(
                f"hypothesis {i} risk_class '{rc}' unknown; use one of "
                + "/".join(r.value for r in RiskClass))
            continue
        hyps.append(Hypothesis(
            action_name=h["action_name"], params=h["params"],
            rationale=h.get("rationale", ""), expected=h.get("expected", {}),
            success_prob=float(sp), confidence=float(h.get("confidence", 0.8)),
            risk_class=h.get("risk_class", RiskClass.READ_ONLY.value),
            derived_from=list(h.get("derived_from", []))))
    if errors:
        return None, errors
    return CognitiveResponse(
        role=raw["role"], summary=raw["summary"], hypotheses=hyps,
        assumptions=list(raw.get("assumptions", [])),
        risks=list(raw.get("risks", [])),
        missing_information=list(raw.get("missing_information", [])),
        confidence=float(raw.get("confidence", 0.8))), []


class LlmGateway:
    def __init__(self, runtime, adapter: LlmPort, config: Config | None = None):
        self.runtime = runtime
        self.adapter = adapter
        self.config = config or Config()

    def ask(self, role: str, context: dict) -> CognitiveResponse:
        """Instructions (role) and data (context) travel in separate fields;
        untrusted content inside the context stays labeled as data."""
        request = {"role": role, "context": context, "schema": SCHEMA_VERSION}
        attempts = 0
        errors: list[str] = []
        while attempts <= self.config.gateway_max_repairs:
            req = dict(request)
            if errors:
                req["repair"] = errors
            self.runtime.emit(Ev.LLM_REQUEST,
                              {"role": role, "digest": _digest(req), "request": req},
                              Actor.SYSTEM)
            raw = self.adapter.generate(req)
            self.runtime.emit(Ev.LLM_RESPONSE,
                              {"role": role, "raw": raw}, Actor.SYSTEM)
            # cost accounting per cognitive function (M13): adapters may
            # report real usage in "_usage"; otherwise a deterministic
            # size-based estimate keeps replay byte-identical
            usage = raw.get("_usage") if isinstance(raw, dict) else None
            if isinstance(usage, dict):
                usage = {"input_tokens": int(usage.get("input_tokens", 0)),
                         "output_tokens": int(usage.get("output_tokens", 0)),
                         "estimated": False}
            else:
                usage = {"input_tokens":
                         len(json.dumps(req, sort_keys=True)) // 4,
                         "output_tokens":
                         len(json.dumps(raw, sort_keys=True, default=str)) // 4,
                         "estimated": True}
            self.runtime.emit(Ev.LLM_USAGE, {"role": role, **usage},
                              Actor.SYSTEM)
            response, errors = validate_response(raw)
            if response is not None:
                return response
            attempts += 1
        self.runtime.emit(Ev.ERROR_DETECTED,
                          {"class": "gateway_schema_error", "errors": errors},
                          Actor.SYSTEM)
        raise GatewayError(f"invalid LLM output after repair: {errors}")


class LlmUsageProjection:
    """Per-cognitive-function accounting of LLM calls and tokens - the
    inference budget is a resource like money (spec: cost accounting
    per cognitive function)."""

    def __init__(self):
        self.roles: dict[str, dict] = {}

    def apply(self, ev) -> None:
        if ev.type != Ev.LLM_USAGE.value:
            return
        p = ev.payload
        r = self.roles.setdefault(p.get("role", "?"),
                                  {"calls": 0, "input_tokens": 0,
                                   "output_tokens": 0, "estimated": True})
        r["calls"] += 1
        r["input_tokens"] += int(p.get("input_tokens", 0))
        r["output_tokens"] += int(p.get("output_tokens", 0))
        if not p.get("estimated", True):
            r["estimated"] = False

    def snapshot(self) -> dict:
        return {k: dict(v) for k, v in sorted(self.roles.items())}


class ReplayLlmAdapter:
    """Serves recorded LLM_RESPONSE events in order; verifies request
    digests so a divergent replay fails loudly instead of silently."""

    def __init__(self, events: list, strict: bool = True):
        self._responses = [e.payload["raw"] for e in events if e.type == Ev.LLM_RESPONSE.value]
        self._digests = [e.payload["digest"] for e in events if e.type == Ev.LLM_REQUEST.value]
        self._i = 0
        self.strict = strict

    def generate(self, request: dict) -> dict:
        if self._i >= len(self._responses):
            raise GatewayError("replay exhausted: more requests than recorded responses")
        if self.strict and _digest(request) != self._digests[self._i]:
            raise GatewayError(f"replay divergence at call {self._i}: request differs from recording")
        raw = self._responses[self._i]
        self._i += 1
        return raw


def run_conformance(adapter: LlmPort, sample_requests: list[dict]) -> list[str]:
    """Port conformance suite: an adapter must produce schema-valid output
    for the sample requests before it may serve the loop."""
    problems: list[str] = []
    for i, req in enumerate(sample_requests):
        try:
            raw = adapter.generate(dict(req, schema=SCHEMA_VERSION))
        except Exception as exc:  # noqa: BLE001 - conformance reports, not crashes
            problems.append(f"request {i}: adapter raised {exc!r}")
            continue
        _, errors = validate_response(raw)
        problems.extend(f"request {i}: {e}" for e in errors)
    return problems
