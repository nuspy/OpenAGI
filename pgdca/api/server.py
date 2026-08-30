"""API-first backend: REST + SSE over the controller.

The GUI reads projections and writes commands; every manual change
becomes an event with human provenance. Authorization applies to GUI
commands exactly as to system actions - the actor identity comes from
the X-Actor header (Phase 0 stub; real authentication is a later
slice) and Tier 1 / ratchet / ratification guarantees are enforced by
the same store-level checks the system itself is subject to.
"""
from __future__ import annotations

import asyncio
import json
from pathlib import Path

from fastapi import Body, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse, StreamingResponse

from ..controller import Controller
from ..domain import NodeKind
from ..events import Actor, Ev

UI_DIR = Path(__file__).resolve().parent.parent / "ui"


def _actor(header_value: str | None) -> Actor:
    v = (header_value or "human").lower()
    try:
        return Actor(v)
    except ValueError:
        raise HTTPException(400, f"unknown actor '{v}'")


def _note(body: dict, x_user: str | None) -> str:
    """Operator identity: the X-User name is stamped into the human
    note so the journal records who decided, not just that a human did."""
    note = str(body.get("note", ""))
    user = (x_user or "").strip()
    return f"{note} [by {user}]".strip() if user else note


def create_app(ctrl: Controller) -> FastAPI:
    app = FastAPI(title="PGDCA Phase 0", version="0.1.0")

    def guard(fn):
        try:
            return fn()
        except PermissionError as exc:
            raise HTTPException(403, str(exc))
        except KeyError as exc:
            raise HTTPException(404, str(exc))
        except ValueError as exc:
            raise HTTPException(409, str(exc))

    # ------------------------------------------------------------- reads
    @app.get("/api/state")
    def state():
        pend = ctrl.pending_decision()
        return {
            "state": ctrl.state.value,
            "cycle": ctrl.cycle,
            "budgets": ctrl.budgets.snapshot(),
            "calibration": ctrl.calibration.snapshot(),
            "pending": pend["decision"].to_dict() if pend else None,
            "pending_verdict": pend["verdict"] if pend else None,
            "open_targets": [t["id"] for t in ctrl.graph.open_targets()],
            "last_seq": ctrl.runtime.store.last_seq(),
        }

    @app.get("/api/graph")
    def graph():
        return ctrl.graph.snapshot()

    @app.get("/api/guardrails")
    def guardrails():
        return ctrl.guardrails.snapshot()

    @app.get("/api/policies")
    def policies():
        return ctrl.policies.snapshot()

    @app.get("/api/strategies")
    def strategies():
        return ctrl.strategies.snapshot()

    @app.get("/api/selfmodel")
    def selfmodel():
        snap = ctrl.self_model.snapshot()
        snap["calibration"] = ctrl.calibration.snapshot()
        return snap

    @app.get("/api/evidence")
    def evidence():
        return ctrl.evidence_store.snapshot()

    @app.post("/api/contradictions/{contradiction_id}/resolve")
    def resolve_contradiction(contradiction_id: str, body: dict = Body(...),
                              x_actor: str | None = Header(default=None)):
        guard(lambda: ctrl.evidence.resolve(contradiction_id,
                                            body.get("status", "UNRESOLVED"),
                                            _actor(x_actor),
                                            body.get("note", "")))
        return {"ok": True}

    @app.get("/api/capabilities")
    def capabilities():
        snap = ctrl.capability_store.snapshot()
        snap["tools"] = [{"name": s.name, "risk_class": s.risk_class,
                          "description": s.description, "enabled": s.enabled,
                          "provenance": s.provenance,
                          "description_trust": s.description_trust}
                         for s in ctrl.registry.specs()]
        return snap

    @app.get("/api/inbox")
    def inbox():
        return {"pending": list(ctrl.inbox.pending.values()),
                "recent": ctrl.inbox.recent[-20:],
                "overrides": ctrl.inbox.overrides[-20:]}

    @app.get("/api/journal")
    def journal(n: int = 30):
        return ctrl.journal.tail(n)

    @app.get("/api/journal/{decision_id}")
    def rationale(decision_id: str):
        r = ctrl.journal.rationale(decision_id)
        if r is None:
            raise HTTPException(404, decision_id)
        return r

    @app.get("/api/events")
    def events(after: int = 0, limit: int = 200):
        evs = ctrl.runtime.events(after)[:limit]
        return [e.to_dict() for e in evs]

    # ------------------------------------------------------ deliberation
    @app.get("/api/deliberations")
    def deliberations():
        return ctrl.deliberations.snapshot()

    @app.post("/api/deliberations")
    def open_deliberation(body: dict = Body(...),
                          x_actor: str | None = Header(default=None)):
        return guard(lambda: ctrl.open_deliberation(
            body.get("subject_kind", ""), body.get("subject_id", ""),
            body.get("question", ""), _actor(x_actor)))

    @app.post("/api/deliberations/{thread_id}/reply")
    def reply_deliberation(thread_id: str, body: dict = Body(...),
                           x_actor: str | None = Header(default=None)):
        return guard(lambda: ctrl.reply_deliberation(
            thread_id, body.get("text", ""), _actor(x_actor)))

    @app.post("/api/deliberations/{thread_id}/resolve")
    def resolve_deliberation(thread_id: str, body: dict = Body(...),
                             x_actor: str | None = Header(default=None)):
        return guard(lambda: ctrl.resolve_deliberation(
            thread_id, body.get("outcome", ""), body.get("note", ""),
            body.get("changes"), _actor(x_actor)))

    @app.get("/api/nodes/{node_id}/decisions")
    def node_decisions(node_id: str):
        node = ctrl.graph.node(node_id)
        if node is None:
            raise HTTPException(404, node_id)
        return {"node": node, "decisions": ctrl.journal.for_node(node_id)}

    # ----------------------------------------------------------- writes
    @app.post("/api/graph/nodes/{node_id}")
    def edit_node(node_id: str, body: dict = Body(...),
                  x_actor: str | None = Header(default=None)):
        actor = _actor(x_actor)
        if ctrl.graph.node(node_id) is None:
            raise HTTPException(404, node_id)
        return guard(lambda: ctrl.human_edit_node(
            node_id, body.get("props", {}), actor, body.get("status"))) or {"ok": True}

    @app.post("/api/guardrails")
    def create_guardrail(body: dict = Body(...),
                         x_actor: str | None = Header(default=None)):
        from ..security.guardrails import Flexibility, guardrail
        actor = _actor(x_actor)
        g = guardrail(
            description=body["description"], tier=int(body["tier"]),
            rule=body["rule"],
            flexibility=Flexibility(body.get("flexibility", "HARD_BLOCK")),
            direction=body.get("direction", "restrictive"),
            conditions=body.get("conditions"), exceptions=body.get("exceptions"),
            provenance="human_gui" if actor == Actor.HUMAN else "system",
            id=body.get("id"))
        return guard(lambda: ctrl.guardrails.create(g, actor))

    @app.post("/api/guardrails/{guardrail_id}")
    def update_guardrail(guardrail_id: str, body: dict = Body(...),
                         x_actor: str | None = Header(default=None)):
        actor = _actor(x_actor)
        guard(lambda: ctrl.guardrails.update(guardrail_id, body.get("changes", {}),
                                             actor))
        return {"ok": True}

    @app.post("/api/guardrails/{guardrail_id}/approve")
    def approve_guardrail(guardrail_id: str,
                          x_actor: str | None = Header(default=None)):
        guard(lambda: ctrl.guardrails.approve_pending(guardrail_id, _actor(x_actor)))
        return {"ok": True}

    @app.post("/api/budget")
    def set_budget(body: dict = Body(...),
                   x_actor: str | None = Header(default=None)):
        guard(lambda: ctrl.set_budget(body["name"], float(body["limit"]),
                                      _actor(x_actor)))
        return {"ok": True}

    @app.post("/api/goals")
    def propose_goal(body: dict = Body(...),
                     x_actor: str | None = Header(default=None)):
        gid = ctrl.propose_goal(NodeKind(body.get("kind", "PERSISTENT_GOAL")),
                                body["label"], float(body.get("priority", 0.5)),
                                _actor(x_actor))
        return {"id": gid}

    @app.post("/api/goals/{node_id}/ratify")
    def ratify(node_id: str, x_actor: str | None = Header(default=None)):
        guard(lambda: ctrl.ratify_goal(node_id, _actor(x_actor)))
        return {"ok": True}

    @app.post("/api/ingest")
    def ingest(body: dict = Body(...)):
        cid = ctrl.ingest_external(body["text"], body.get("source", "gui"))
        return {"content_id": cid}

    # ------------------------------------------------------- capabilities
    @app.post("/api/skills/import")
    def import_skill(body: dict = Body(...),
                     x_actor: str | None = Header(default=None)):
        try:
            return guard(lambda: ctrl.import_skill(body["path"], _actor(x_actor)))
        except Exception as exc:  # validation errors -> 400
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(400, str(exc))

    @app.post("/api/skills/{name}")
    def set_skill(name: str, body: dict = Body(...),
                  x_actor: str | None = Header(default=None)):
        guard(lambda: ctrl.set_skill_enabled(name, bool(body.get("enabled")),
                                             _actor(x_actor)))
        return {"ok": True}

    @app.post("/api/mcp/import")
    def import_mcp(body: dict = Body(...),
                   x_actor: str | None = Header(default=None)):
        try:
            return guard(lambda: ctrl.import_mcp_server(
                body["server_id"], list(body["command"]), _actor(x_actor)))
        except Exception as exc:
            if isinstance(exc, HTTPException):
                raise
            raise HTTPException(400, str(exc))

    @app.post("/api/mcp/{server_id}/approve")
    def approve_mcp(server_id: str, x_actor: str | None = Header(default=None)):
        guard(lambda: ctrl.approve_mcp_server(server_id, _actor(x_actor)))
        return {"ok": True}

    @app.post("/api/tools/{name}")
    def set_tool(name: str, body: dict = Body(...),
                 x_actor: str | None = Header(default=None)):
        guard(lambda: ctrl.set_tool_enabled(name, bool(body.get("enabled")),
                                            _actor(x_actor)))
        return {"ok": True}

    @app.post("/api/capabilities/verify")
    def verify_capabilities():
        return {"quarantined": ctrl.verify_capabilities()}

    @app.get("/api/llmusage")
    def llm_usage():
        return ctrl.llm_usage.snapshot()

    # ------------------------------- LLM provider selection (llmswitch)
    def _llmswitch_registry():
        """The local llmswitch registry, or None when the library is not
        installed. Secrets stay in its file outside the repo; only
        `public()` (keys reduced to a boolean) ever crosses this API."""
        try:
            from llmswitch import Registry
        except ImportError:
            return None
        import os
        return Registry(app_name=os.environ.get("PGDCA_LLMSWITCH_APP",
                                                "pgdca"))

    def _require_human(x_actor: str | None) -> None:
        # picking who does the thinking is a human decision, like enabling
        # a risky tool (promotion is never system-initiated)
        if _actor(x_actor) != Actor.HUMAN:
            raise HTTPException(403, "LLM provider changes are human-only")

    def _registry_or_409():
        reg = _llmswitch_registry()
        if reg is None:
            raise HTTPException(409, "llmswitch is not installed in this "
                                     "environment (pip install -e "
                                     "C:/Projects/llmswitch)")
        return reg

    @app.get("/api/llm")
    def llm_info():
        adapter = ctrl.gateway.adapter
        out = {"adapter": type(adapter).__name__,
               "model_by_role": dict(getattr(adapter, "model_by_role",
                                             None) or {}),
               "consumer_by_role": dict(getattr(adapter, "consumer_by_role",
                                                None) or {})}
        reg = _llmswitch_registry()
        if reg is None:
            out["llmswitch"] = {"available": False}
        else:
            out["llmswitch"] = {"available": True,
                                "registry_path": str(reg.path),
                                **reg.public()}
        return out

    @app.post("/api/llm/adapter")
    def llm_switch_adapter(body: dict = Body(...),
                           x_actor: str | None = Header(default=None)):
        _require_human(x_actor)
        kind = str(body.get("type", "")).strip()
        if kind == "mock":
            from ..cognition.mock_llm import MockLlmAdapter
            adapter = MockLlmAdapter()
        elif kind == "anthropic":
            try:
                from ..cognition.anthropic_adapter import AnthropicLlmAdapter
                adapter = AnthropicLlmAdapter()
            except Exception as exc:  # noqa: BLE001 - SDK/credentials missing
                raise HTTPException(409, f"anthropic adapter unavailable: {exc}")
        elif kind == "llmswitch":
            _registry_or_409()
            try:
                from examples.adapters.local_llm_provider_adapter import (
                    LocalProviderAdapter,
                )
                adapter = LocalProviderAdapter()
            except Exception as exc:  # noqa: BLE001 - run from the repo root
                raise HTTPException(409, f"llmswitch adapter unavailable: {exc}")
        else:
            raise HTTPException(400, f"unknown adapter type '{kind}'")
        ctrl.gateway.adapter = adapter
        # auditable, and reapplied as a no-op on recovery (unknown config key)
        ctrl.runtime.emit(Ev.CONFIG_UPDATED,
                          {"changes": {"llm_adapter": kind}}, Actor.HUMAN)
        return {"adapter": type(adapter).__name__}

    @app.post("/api/llm/providers")
    def llm_add_provider(body: dict = Body(...),
                         x_actor: str | None = Header(default=None)):
        _require_human(x_actor)
        reg = _registry_or_409()
        voce = guard(lambda: reg.add(body))
        return {"id": voce["id"], "type": voce["type"]}

    @app.post("/api/llm/providers/{pid}")
    def llm_update_provider(pid: str, body: dict = Body(...),
                            x_actor: str | None = Header(default=None)):
        _require_human(x_actor)
        reg = _registry_or_409()
        guard(lambda: reg.update(pid, body))
        return {"id": pid}

    @app.post("/api/llm/providers/{pid}/remove")
    def llm_remove_provider(pid: str,
                            x_actor: str | None = Header(default=None)):
        _require_human(x_actor)
        reg = _registry_or_409()
        reg.remove(pid)
        return {"removed": pid}

    @app.get("/api/llm/providers/{pid}/models")
    def llm_provider_models(pid: str):
        reg = _registry_or_409()
        try:
            return {"models": reg.models(pid, force=True)}
        except KeyError as exc:
            raise HTTPException(404, str(exc))
        except Exception as exc:  # noqa: BLE001 - provider unreachable
            raise HTTPException(502, str(exc))

    @app.post("/api/llm/providers/{pid}/test")
    def llm_test_provider(pid: str):
        reg = _registry_or_409()
        return reg.test(pid)

    @app.post("/api/llm/assign")
    def llm_assign(body: dict = Body(...),
                   x_actor: str | None = Header(default=None)):
        _require_human(x_actor)
        reg = _registry_or_409()
        assignments = guard(lambda: reg.assign(
            str(body.get("consumer", "")), body.get("provider_id") or None))
        return {"assignments": assignments}

    # -------------------------------------------- exogenous inputs (M31)
    @app.get("/api/exogenous")
    def exogenous():
        return ctrl.exogenous.snapshot()

    @app.post("/api/directives")
    def issue_directive(body: dict = Body(...),
                        x_actor: str | None = Header(default=None)):
        return guard(lambda: ctrl.exogenous.issue_directive(
            body["label"], body.get("description", ""),
            float(body.get("weight", 0.6)), body.get("horizon", "short"),
            body.get("directive_type", "context"), _actor(x_actor)))

    @app.post("/api/facts")
    def record_fact(body: dict = Body(...),
                    x_actor: str | None = Header(default=None)):
        return guard(lambda: ctrl.exogenous.record_fact(
            body["label"], body.get("description", ""),
            float(body.get("weight", 0.5)), body.get("mode", "imposed"),
            _actor(x_actor)))

    @app.post("/api/exogenous/{node_id}/update")
    def update_exogenous(node_id: str, body: dict = Body(...),
                         x_actor: str | None = Header(default=None)):
        guard(lambda: ctrl.exogenous.update(node_id, body.get("props", {}),
                                            _actor(x_actor)))
        return {"ok": True}

    @app.post("/api/exogenous/{node_id}/retire")
    def retire_exogenous(node_id: str, body: dict = Body(default={}),
                         x_actor: str | None = Header(default=None)):
        return guard(lambda: ctrl.exogenous.retire(
            node_id, _actor(x_actor), body.get("note", "")))

    @app.post("/api/exogenous/{node_id}/reintegrate")
    def reintegrate_exogenous(node_id: str,
                              x_actor: str | None = Header(default=None)):
        guard(lambda: ctrl.exogenous.reintegrate(node_id, _actor(x_actor)))
        return {"ok": True}

    @app.post("/api/exogenous/{node_id}/accept")
    def accept_opportunity(node_id: str,
                           x_actor: str | None = Header(default=None)):
        return guard(lambda: ctrl.accept_opportunity(node_id, _actor(x_actor)))

    @app.post("/api/exogenous/{node_id}/decline")
    def decline_opportunity(node_id: str,
                            x_actor: str | None = Header(default=None)):
        return guard(lambda: ctrl.decline_opportunity(node_id,
                                                      _actor(x_actor)))

    # -------------------------------------------- review / grounding
    @app.get("/api/reviews")
    def reviews():
        return ctrl.reviews.snapshot()

    @app.get("/api/knowledge")
    def knowledge():
        return ctrl.grounding.snapshot()

    @app.post("/api/knowledge")
    def add_knowledge(body: dict = Body(...),
                      x_actor: str | None = Header(default=None)):
        kid = guard(lambda: ctrl.add_knowledge(
            body.get("text", ""), body.get("meta"), _actor(x_actor)))
        return {"id": kid}

    # ---------------------------------------------------------- control
    @app.post("/api/control/{command}")
    def control(command: str, x_actor: str | None = Header(default=None)):
        guard(lambda: ctrl.control(command, _actor(x_actor)))
        return {"state": ctrl.state.value}

    @app.post("/api/step")
    def step(body: dict = Body(default={})):
        n = int(body.get("n", 1))
        results = [ctrl.step().__dict__ for _ in range(max(1, min(n, 50)))]
        return {"results": results, "state": ctrl.state.value}

    @app.post("/api/pending/resolve")
    def resolve(body: dict = Body(...),
                x_actor: str | None = Header(default=None),
                x_user: str | None = Header(default=None)):
        actor = _actor(x_actor)
        if actor != Actor.HUMAN:
            raise HTTPException(403, "pending decisions are resolved by the human")
        r = ctrl.resolve_pending(bool(body.get("approve")), _note(body, x_user))
        return {"result": r.__dict__ if r else None, "state": ctrl.state.value}

    @app.post("/api/verdicts/{verdict_id}/override")
    def override(verdict_id: str, body: dict = Body(...),
                 x_actor: str | None = Header(default=None),
                 x_user: str | None = Header(default=None)):
        actor = _actor(x_actor)
        if actor != Actor.HUMAN:
            raise HTTPException(403, "overrides belong to the human identity")
        return guard(lambda: ctrl.override_verdict(
            verdict_id, bool(body.get("approve")), _note(body, x_user)))

    # ------------------------------------------------------ configuration
    @app.get("/api/config")
    def get_config():
        import dataclasses
        return dataclasses.asdict(ctrl.config)

    @app.post("/api/config")
    def set_config(body: dict = Body(...),
                   x_actor: str | None = Header(default=None)):
        return guard(lambda: ctrl.update_config(
            body.get("changes", {}), _actor(x_actor)))

    # --------------------------------------------------------------- SSE
    @app.get("/api/events/stream")
    async def stream(after: int = 0):
        async def gen():
            last = after
            while True:
                evs = ctrl.runtime.events(last)
                for e in evs:
                    last = e.seq
                    yield f"data: {json.dumps(e.to_dict())}\n\n"
                await asyncio.sleep(0.7)
        return StreamingResponse(gen(), media_type="text/event-stream")

    # ---------------------------------------------------------------- UI
    @app.get("/")
    def index():
        return FileResponse(UI_DIR / "index.html")

    return app


def main() -> None:  # pragma: no cover - manual server entrypoint
    import argparse

    import uvicorn

    from ..scenario.toy import create

    parser = argparse.ArgumentParser(description="PGDCA server")
    parser.add_argument("--db", default=":memory:", help="event store path")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--adapter", choices=["mock", "anthropic", "llmswitch"],
                        default="mock",
                        help="LLM adapter behind the port (anthropic requires "
                             "the SDK and credentials; server-side refusal "
                             "fallbacks are enabled by default; llmswitch "
                             "requires the local library and a configured "
                             "registry - docs/LOCAL_INTEGRATIONS.md)")
    args = parser.parse_args()

    adapter = None
    if args.adapter == "anthropic":
        from ..cognition.anthropic_adapter import AnthropicLlmAdapter
        adapter = AnthropicLlmAdapter()
    elif args.adapter == "llmswitch":
        # local integration: run from the repo root so `examples` resolves
        from examples.adapters.local_llm_provider_adapter import (
            LocalProviderAdapter,
        )
        adapter = LocalProviderAdapter()
    ctrl, _env = create(db_path=args.db, adapter=adapter)
    # expose the local-integration connection points (disabled until real
    # adapters are wired in local development - docs/LOCAL_INTEGRATIONS.md)
    from ..tools.external import register_external_ports
    register_external_ports(ctrl.registry)
    app = create_app(ctrl)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":  # pragma: no cover
    main()
