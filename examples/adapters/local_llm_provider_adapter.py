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
#: agents (seconds per reply, no completion endpoint); Cloud Code is not
#: OpenAI-compatible. The Anthropic dialect IS supported: it routes through
#: the reference adapter internally, so the registry stays the single place
#: where providers are chosen.
_UNSUPPORTED_API = {
    "cli": "CLI agent providers have no completion endpoint - assign an "
           "HTTP provider to this consumer",
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
        self._anthropic_cache: dict = {}

    # ------------------------------------------------------------- resolve

    def _provider_api(self, consumer: str) -> tuple[dict, str]:
        """(provider record, api family) for a consumer; refuses families
        that cannot serve the gateway loop."""
        prov = self.registry.provider_for(consumer) or {}
        try:
            from llmswitch import TYPES
        except ImportError:   # injected registry in tests, no library around
            return prov, "openai"
        api = (TYPES.get(prov.get("type") or "", {}) or {}).get("api",
                                                                "openai")
        if api in _UNSUPPORTED_API:
            raise RuntimeError(
                f"llmswitch provider '{prov.get('type')}' for consumer "
                f"'{consumer}': {_UNSUPPORTED_API[api]}")
        return prov, api

    def _anthropic_for(self, key: str, base: str, model: str):
        """Anthropic-dialect providers route through the reference adapter:
        the registry stays the only place where providers are chosen."""
        cache_key = (key, base, model)
        if cache_key not in self._anthropic_cache:
            try:
                import anthropic
            except ImportError:
                raise RuntimeError(
                    "provider Anthropic nel registro llmswitch ma SDK "
                    "assente: pip install -e .[anthropic]")
            from pgdca.cognition.anthropic_adapter import AnthropicLlmAdapter
            kwargs: dict = {}
            if key:
                kwargs["api_key"] = key
            if base:
                # only an EXPLICIT custom base overrides the SDK default
                # (the registry's chat_base_url already ends in /v1, which
                # the SDK would double)
                kwargs["base_url"] = base
            self._anthropic_cache[cache_key] = AnthropicLlmAdapter(
                model=model or None, client=anthropic.Anthropic(**kwargs),
                model_by_role=self.model_by_role)
        return self._anthropic_cache[cache_key]

    def _ensure_assignment(self, consumer: str) -> None:
        """Self-heal a common dead-end: a provider exists but nothing is
        assigned to this consumer, so the whole system silently can't think.
        With a single provider the choice is unambiguous - assign it."""
        if self.registry.provider_for(consumer) is not None:
            return
        try:
            provs = self.registry.load().get("providers", [])
        except Exception:  # noqa: BLE001 - injected registries in tests
            return
        if len(provs) == 1:
            try:
                self.registry.assign(consumer, provs[0]["id"])
            except Exception:  # noqa: BLE001
                pass

    def _endpoint(self, role: str) -> tuple[str, dict, str]:
        consumer = self.consumer_by_role.get(role, self.consumer)
        self._ensure_assignment(consumer)
        resolved = self.registry.endpoint_for(consumer, carica=self.carica)
        if resolved is None:
            provs = []
            try:
                provs = self.registry.load().get("providers", [])
            except Exception:  # noqa: BLE001
                pass
            hint = ("nessun provider configurato: aprine uno dal tab "
                    "'LLM & Collegamenti'" if not provs
                    else f"scegli il provider per '{consumer}' nel tab "
                    "'LLM & Collegamenti' (Assegnazioni)")
            raise RuntimeError(
                f"llmswitch: {hint} "
                f"(registro {getattr(self.registry, 'path', '?')})")
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
        role = str(request.get("role", ""))
        consumer = self.consumer_by_role.get(role, self.consumer)
        prov, api = self._provider_api(consumer)
        if api == "anthropic":
            key = (prov.get("api_key") or "").strip()
            model = self.model_by_role.get(role) or \
                (prov.get("model") or "").strip()
            return self._anthropic_for(key, (prov.get("base_url") or "").strip(),
                                       model).generate(request)
        base, headers, model = self._endpoint(role)
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
