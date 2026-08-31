"""llmswitch adapter behind the LLM port (fake registry/transport, no network).

The real library and registry live only on the owner's machine: these tests
inject fakes so they run everywhere. The live check (real llmswitch registry,
real endpoint) is opt-in via PGDCA_LLMSWITCH_LIVE=1.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.adapters.local_llm_provider_adapter import LocalProviderAdapter  # noqa: E402
from pgdca.cognition.anthropic_adapter import SYSTEM_PROMPT  # noqa: E402
from pgdca.cognition.gateway import SCHEMA_VERSION, run_conformance  # noqa: E402

VALID = {"schema": SCHEMA_VERSION, "role": "hypotheses", "summary": "ok",
         "hypotheses": [], "assumptions": [], "risks": [],
         "missing_information": [], "confidence": 0.8}


class FakeRegistry:
    def __init__(self, endpoints):
        # endpoints: consumer -> (base, key, model) | None
        self.endpoints = endpoints
        self.path = "<fake>"

    def provider_for(self, consumer):
        return {"type": "openai_compat"} if self.endpoints.get(consumer) else None

    def endpoint_for(self, consumer, embedding=False, carica=True):
        return self.endpoints.get(consumer)

    def headers_for(self, consumer):
        ep = self.endpoints.get(consumer)
        key = ep[1] if ep else ""
        return {"Authorization": f"Bearer {key}"} if key and key != "local" else {}


class FakePost:
    def __init__(self, text, usage=None):
        self.calls = []
        self.text = text
        self.usage = usage

    def __call__(self, url, json=None, headers=None, timeout=None):
        self.calls.append({"url": url, "json": json, "headers": headers})
        body = {"choices": [{"message": {"content": self.text}}]}
        if self.usage:
            body["usage"] = self.usage
        outer = self

        class _Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return body
        return _Resp()


def make(post, endpoints=None, **kw):
    if endpoints is None:
        endpoints = {"chat": ("http://127.0.0.1:1234/v1", "local", "m-big")}
    reg = FakeRegistry(endpoints)
    return LocalProviderAdapter(registry=reg, http_post=post, **kw)


def test_conformance_and_data_framing():
    post = FakePost(json.dumps(VALID))
    adapter = make(post)
    assert run_conformance(adapter, [
        {"role": "hypotheses", "context": {"factors": [], "goals": []}}]) == []
    call = post.calls[0]
    assert call["url"] == "http://127.0.0.1:1234/v1/chat/completions"
    msgs = call["json"]["messages"]
    # instructions in the system prompt, the request as DATA in the user turn
    assert msgs[0] == {"role": "system", "content": SYSTEM_PROMPT}
    sent = json.loads(msgs[1]["content"])
    assert sent["role"] == "hypotheses" and "context" in sent


def test_real_usage_attached_as__usage():
    post = FakePost(json.dumps(VALID),
                    usage={"prompt_tokens": 11, "completion_tokens": 7})
    out = make(post).generate({"role": "hypotheses", "context": {}})
    assert out["_usage"] == {"input_tokens": 11, "output_tokens": 7}


def test_fenced_json_tolerated():
    post = FakePost("sure:\n```json\n" + json.dumps(VALID) + "\n```")
    out = make(post).generate({"role": "hypotheses", "context": {}})
    assert out["schema"] == SCHEMA_VERSION


def test_m13_routing_by_role():
    post = FakePost(json.dumps(VALID))
    adapter = make(post, endpoints={
        "chat": ("http://big/v1", "local", "m-big"),
        "copilot": ("http://small/v1", "local", "m-small")},
        consumer_by_role={"classify": "copilot"},
        model_by_role={"causal": "m-override"})
    adapter.generate({"role": "hypotheses", "context": {}})
    adapter.generate({"role": "classify", "context": {}})
    adapter.generate({"role": "causal", "context": {}})
    assert [c["url"] for c in post.calls] == [
        "http://big/v1/chat/completions",
        "http://small/v1/chat/completions",
        "http://big/v1/chat/completions"]
    assert [c["json"]["model"] for c in post.calls] == [
        "m-big", "m-small", "m-override"]


def test_missing_assignment_is_a_clear_error():
    adapter = make(FakePost(json.dumps(VALID)), endpoints={})
    problems = run_conformance(adapter, [{"role": "hypotheses", "context": {}}])
    # the message now guides the user to the LLM tab instead of jargon
    assert problems and "LLM & Collegamenti" in problems[0]


def test_bearer_header_from_key_but_not_for_local():
    post = FakePost(json.dumps(VALID))
    adapter = make(post, endpoints={"chat": ("http://x/v1", "sk-abc", "m")})
    adapter.generate({"role": "hypotheses", "context": {}})
    assert post.calls[0]["headers"]["Authorization"] == "Bearer sk-abc"
    post2 = FakePost(json.dumps(VALID))
    make(post2).generate({"role": "hypotheses", "context": {}})
    assert "Authorization" not in post2.calls[0]["headers"]


@pytest.mark.skipif(importlib.util.find_spec("llmswitch") is None,
                    reason="needs llmswitch TYPES for the api-family lookup")
def test_anthropic_provider_routes_through_reference_adapter(monkeypatch):
    """The registry is the ONLY place providers are chosen: a 'claude' entry
    must route through the Anthropic reference adapter, not /chat/completions."""
    class ClaudeRegistry(FakeRegistry):
        def provider_for(self, consumer):
            return {"type": "claude", "api_key": "sk-a",
                    "model": "claude-opus-5", "base_url": ""}

    post = FakePost(json.dumps(VALID))
    adapter = LocalProviderAdapter(registry=ClaudeRegistry({}), http_post=post)
    seen = {}

    class FakeAnthropicAdapter:
        def generate(self, request):
            seen["request"] = request
            return dict(VALID)

    monkeypatch.setattr(adapter, "_anthropic_for",
                        lambda key, base, model:
                        seen.update(resolved=(key, base, model))
                        or FakeAnthropicAdapter())
    out = adapter.generate({"role": "hypotheses", "context": {}})
    assert out["schema"] == SCHEMA_VERSION
    assert seen["resolved"] == ("sk-a", "", "claude-opus-5")
    assert not post.calls          # never hit the OpenAI-dialect path


@pytest.mark.skipif(
    os.environ.get("PGDCA_LLMSWITCH_LIVE") != "1"
    or importlib.util.find_spec("llmswitch") is None,
    reason="live llmswitch check is opt-in (PGDCA_LLMSWITCH_LIVE=1 + library)")
def test_live_conformance_against_real_registry():
    problems = run_conformance(LocalProviderAdapter(), [
        {"role": "hypotheses", "context": {"factors": [], "goals": []}}])
    assert problems == []
