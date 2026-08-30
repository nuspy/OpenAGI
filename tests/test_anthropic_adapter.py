"""Reference Anthropic adapter behind the LLM port (fake client, no network)."""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from pgdca.cognition.anthropic_adapter import AnthropicLlmAdapter, _extract_json
from pgdca.cognition.gateway import SCHEMA_VERSION, run_conformance

VALID = {"schema": SCHEMA_VERSION, "role": "hypotheses", "summary": "ok",
         "hypotheses": [], "assumptions": [], "risks": [],
         "missing_information": [], "confidence": 0.8}


class FakeClient:
    def __init__(self, text, stop_reason="end_turn"):
        self.calls = []
        outer = self

        class _Messages:
            def create(self, **kw):
                outer.calls.append(kw)
                return SimpleNamespace(
                    content=[SimpleNamespace(type="text", text=text)],
                    stop_reason=stop_reason, stop_details=None)

        self.beta = SimpleNamespace(messages=_Messages())
        self.messages = _Messages()


def test_adapter_defaults_and_fallbacks_enabled():
    fake = FakeClient(json.dumps(VALID))
    adapter = AnthropicLlmAdapter(client=fake)
    out = adapter.generate({"role": "hypotheses", "context": {}})
    assert out == VALID
    kw = fake.calls[0]
    assert kw["model"] == "claude-opus-5"
    assert kw["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in kw["betas"]
    assert kw["system"].startswith("You are the generative component")


def test_adapter_tolerates_fenced_json():
    fake = FakeClient("Here you go:\n```json\n" + json.dumps(VALID) + "\n```")
    out = AnthropicLlmAdapter(client=fake).generate({"role": "hypotheses"})
    assert out == VALID


def test_refusal_raises_for_gateway_handling():
    fake = FakeClient("", stop_reason="refusal")
    with pytest.raises(RuntimeError):
        AnthropicLlmAdapter(client=fake).generate({"role": "hypotheses"})


def test_unparseable_output_defers_to_gateway_repair():
    out = _extract_json("no json at all")
    assert "invalid" in out   # gateway validation will reject and repair


def test_adapter_passes_gateway_conformance():
    fake = FakeClient(json.dumps(VALID))
    adapter = AnthropicLlmAdapter(client=fake)
    samples = [{"role": "hypotheses", "context": {}}]
    assert run_conformance(adapter, samples) == []
