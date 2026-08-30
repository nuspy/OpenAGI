"""llmswitch adapter behind the PGDCA LLM port (local integration).

The owner's provider library is `llmswitch` (C:/Projects/llmswitch): a
registry of LLM providers (local engines with the VRAM rule, pay-per-use
APIs, subscriptions) that resolves a *consumer* name to an
OpenAI-compatible endpoint:

    base_url, api_key, model = Registry(app_name=...).endpoint_for("chat")

This adapter keeps the gateway contract of the reference Anthropic
adapter (pgdca/cognition/anthropic_adapter.py):

- instructions live in the system prompt; the request context travels
  as DATA in the user message with the non-trust framing (the injection
  doctrine applies inside the prompt too);
- the response must be a single JSON object matching
  `cognitive_response/1`; the gateway validates and repairs;
- real usage is attached as "_usage" when the provider reports it;
- M13 routing: `consumer_by_role` picks a different llmswitch consumer
  (hence provider/endpoint) per cognitive function, and `model_by_role`
  overrides the model id per role, like the reference adapter.

Configuration (env vars, no secrets in this repo - keys live in the
llmswitch registry file under %LOCALAPPDATA%):

    PGDCA_LLMSWITCH_APP               registry app name   (default "pgdca")
    PGDCA_LLMSWITCH_CONSUMER          default consumer    (default "chat")
    PGDCA_LLMSWITCH_CONSUMER_BY_ROLE  JSON, e.g. {"hypotheses": "chat"}
    PGDCA_LLMSWITCH_MODEL_BY_ROLE     JSON, e.g. {"causal": "gemma-4-12b"}
    PGDCA_LLMSWITCH_CARICA            "0" = never load a model into VRAM
    PGDCA_LLM_MAX_TOKENS              max completion tokens (default 16000)

Validation:

    from pgdca.cognition.gateway import run_conformance
    problems = run_conformance(LocalProviderAdapter(), [
        {"role": "hypotheses", "context": {"factors": [], "goals": []}}])
    assert problems == []          # the adapter is ready

    python -m pgdca.api.server --adapter llmswitch
"""
from __future__ import annotations

import json
import os

# Same instruction/data separation and JSON extraction as the reference
# adapter: one copy of the doctrine, not two drifting ones.
from pgdca.cognition.anthropic_adapter import SYSTEM_PROMPT, _extract_json

#: llmswitch provider families this adapter cannot drive. CLI providers are
#: agents (seconds per reply, no completion endpoint); the Anthropic dialect
#: has its own reference adapter; Cloud Code is not OpenAI-compatible.
_UNSUPPORTED_API = {
    "cli": "CLI agent providers have no completion endpoint - assign an "
           "HTTP provider to this consumer",
    "anthropic": "use pgdca.cognition.anthropic_adapter.AnthropicLlmAdapter "
                 "for Anthropic providers",
    "cloudcode": "Cloud Code is not OpenAI-compatible and rejects "
                 "individual plans (see llmswitch notes)",
}


def _env_json(name: str) -> dict:
    raw = os.environ.get(name, "").strip()
    if not raw:
        return {}
    obj = json.loads(raw)
    if not isinstance(obj, dict):
        raise ValueError(f"{name} must be a JSON object")
    return obj


class LocalProviderAdapter:
    """`LlmPort` adapter over the llmswitch provider registry."""

    def __init__(self, app_name: str | None = None,
                 consumer: str | None = None,
                 consumer_by_role: dict | None = None,
                 model_by_role: dict | None = None,
                 max_tokens: int | None = None,
                 timeout_s: float = 300.0,
                 carica: bool | None = None,
                 registry=None, http_post=None):
        self.consumer = consumer or os.environ.get(
            "PGDCA_LLMSWITCH_CONSUMER", "chat")
        self.consumer_by_role = dict(
            consumer_by_role if consumer_by_role is not None
            else _env_json("PGDCA_LLMSWITCH_CONSUMER_BY_ROLE"))
        self.model_by_role = dict(
            model_by_role if model_by_role is not None
            else _env_json("PGDCA_LLMSWITCH_MODEL_BY_ROLE"))
        self.max_tokens = int(max_tokens or os.environ.get(
            "PGDCA_LLM_MAX_TOKENS", 16000))
        self.timeout_s = timeout_s
        # carica=False: only use a model already warm in VRAM - for runs that
        # must not claim the GPU on their own initiative (llmswitch rule).
        self.carica = (os.environ.get("PGDCA_LLMSWITCH_CARICA", "1") != "0"
                       if carica is None else bool(carica))
        if registry is None:
            from llmswitch import Registry  # deferred: local-only dependency
            registry = Registry(app_name=app_name or os.environ.get(
                "PGDCA_LLMSWITCH_APP", "pgdca"))
        self.registry = registry
        if http_post is None:
            import requests  # deferred: llmswitch's own dependency
            http_post = requests.post
        self._post = http_post

    # ------------------------------------------------------------- resolve

    def _guard_provider(self, consumer: str) -> None:
        """Refuse provider families that cannot serve the gateway loop."""
        prov = self.registry.provider_for(consumer)
        if not prov:
            return
        try:
            from llmswitch import TYPES
        except ImportError:   # injected registry in tests, no library around
            return
        api = (TYPES.get(prov.get("type") or "", {}) or {}).get("api", "")
        if api in _UNSUPPORTED_API:
            raise RuntimeError(
                f"llmswitch provider '{prov.get('type')}' for consumer "
                f"'{consumer}': {_UNSUPPORTED_API[api]}")

    def _endpoint(self, role: str) -> tuple[str, dict, str]:
        consumer = self.consumer_by_role.get(role, self.consumer)
        self._guard_provider(consumer)
        resolved = self.registry.endpoint_for(consumer, carica=self.carica)
        if resolved is None:
            raise RuntimeError(
                f"llmswitch: no provider assigned to consumer '{consumer}' "
                f"(registry {getattr(self.registry, 'path', '?')})")
        base, key, model = resolved
        model = self.model_by_role.get(role) or model
        if not base or not model:
            raise RuntimeError(
                f"llmswitch: consumer '{consumer}' resolved to an empty "
                f"endpoint/model (base={base!r}, model={model!r})")
        headers = dict(self.registry.headers_for(consumer) or {})
        if "Authorization" not in headers and key and key != "local":
            headers["Authorization"] = f"Bearer {key}"
        headers["Content-Type"] = "application/json"
        return base.rstrip("/"), headers, model

    # ------------------------------------------------------------ generate

    def generate(self, request: dict) -> dict:
        base, headers, model = self._endpoint(str(request.get("role", "")))
        payload = {
            "model": model,
            "max_tokens": self.max_tokens,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                # the whole request (role + context + repair) travels as DATA
                {"role": "user",
                 "content": json.dumps(request, ensure_ascii=False)},
            ],
        }
        obj: dict = {"invalid": "no attempt"}
        usage: dict = {}
        # local thinking models occasionally emit unparseable text; one cheap
        # in-adapter retry keeps the gateway's bounded repair budget for
        # actual schema errors instead of burning it on parse noise
        for _ in range(2):
            resp = self._post(base + "/chat/completions", json=payload,
                              headers=headers, timeout=self.timeout_s)
            resp.raise_for_status()
            data = resp.json()
            choices = data.get("choices") or []
            message = (choices[0].get("message") or {}) if choices else {}
            text = message.get("content") or ""
            obj = _extract_json(text)
            if "invalid" in obj and not text.strip():
                # thinking models (e.g. qwen3 on LM Studio) may leave the
                # answer in reasoning_content with an empty content channel
                obj = _extract_json(message.get("reasoning_content") or "")
            usage = data.get("usage") or {}
            if "invalid" not in obj:
                break
        if isinstance(obj, dict) and usage:
            obj["_usage"] = {
                "input_tokens": int(usage.get("prompt_tokens", 0) or 0),
                "output_tokens": int(usage.get("completion_tokens", 0) or 0)}
        return obj
