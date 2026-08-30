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


def create_app(ctrl: Controller) -> FastAPI:
    app = FastAPI(title="PGDCA Phase 0", version="0.1.0")

    def guard(fn):
        try:
            return fn()
        except PermissionError as exc:
            raise HTTPException(403, str(exc))
        except KeyError as exc:
            raise HTTPException(404, str(exc))

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
    @app.post("/api/deliberation/node/{node_id}")
    def deliberate_node(node_id: str, body: dict = Body(default={})):
        ctrl.runtime.emit(Ev.DELIBERATION_OPENED,
                          {"target": node_id, "question": body.get("question", "")},
                          Actor.HUMAN)
        packets = ctrl.journal.for_node(node_id)
        node = ctrl.graph.node(node_id)
        answer = {"node": node, "decisions": packets}
        ctrl.runtime.emit(Ev.DELIBERATION_RESOLVED,
                          {"target": node_id, "decisions": len(packets)},
                          Actor.SYSTEM)
        return answer

    @app.post("/api/deliberation/decision/{decision_id}")
    def deliberate_decision(decision_id: str, body: dict = Body(default={})):
        ctrl.runtime.emit(Ev.DELIBERATION_OPENED,
                          {"target": decision_id, "question": body.get("question", "")},
                          Actor.HUMAN)
        r = ctrl.journal.rationale(decision_id)
        if r is None:
            raise HTTPException(404, decision_id)
        ctrl.runtime.emit(Ev.DELIBERATION_RESOLVED, {"target": decision_id},
                          Actor.SYSTEM)
        return r

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
                x_actor: str | None = Header(default=None)):
        actor = _actor(x_actor)
        if actor != Actor.HUMAN:
            raise HTTPException(403, "pending decisions are resolved by the human")
        r = ctrl.resolve_pending(bool(body.get("approve")), body.get("note", ""))
        return {"result": r.__dict__ if r else None, "state": ctrl.state.value}

    @app.post("/api/verdicts/{verdict_id}/override")
    def override(verdict_id: str, body: dict = Body(...),
                 x_actor: str | None = Header(default=None)):
        actor = _actor(x_actor)
        if actor != Actor.HUMAN:
            raise HTTPException(403, "overrides belong to the human identity")
        return guard(lambda: ctrl.override_verdict(
            verdict_id, bool(body.get("approve")), body.get("note", "")))

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
    parser.add_argument("--adapter", choices=["mock", "anthropic"], default="mock",
                        help="LLM adapter behind the port (anthropic requires "
                             "the SDK and credentials; server-side refusal "
                             "fallbacks are enabled by default)")
    args = parser.parse_args()

    adapter = None
    if args.adapter == "anthropic":
        from ..cognition.anthropic_adapter import AnthropicLlmAdapter
        adapter = AnthropicLlmAdapter()
    ctrl, _env = create(db_path=args.db, adapter=adapter)
    # expose the local-integration connection points (disabled until real
    # adapters are wired in local development - docs/LOCAL_INTEGRATIONS.md)
    from ..tools.external import register_external_ports
    register_external_ports(ctrl.registry)
    app = create_app(ctrl)
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":  # pragma: no cover
    main()
