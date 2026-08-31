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
    import threading

    app = FastAPI(title="PGDCA Phase 0", version="0.1.0")
    # autonomy: the loop advances BY ITSELF (the human supervises, not
    # cranks). The runner thread (started by main) and the GUI's manual
    # controls share this state and this lock.
    app.state.autonomy = {"enabled": True, "interval_s": 3.0,
                          "idle_interval_s": 10.0, "backoff_s": 60.0}
    app.state.ctrl_lock = threading.Lock()

    def guard(fn):
        try:
            return fn()
        except PermissionError as exc:
            raise HTTPException(403, str(exc))
        except KeyError as exc:
            raise HTTPException(404, str(exc))
        except ValueError as exc:
            raise HTTPException(409, str(exc))
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 - the GUI must get JSON,
            # never a bare 500 page it cannot parse
            raise HTTPException(502, f"{type(exc).__name__}: {exc}")

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
            # shown in the GUI header: judging canned mock output as "the
            # system's reasoning" is a real misunderstanding to prevent
            "llm_adapter": type(ctrl.gateway.adapter).__name__,
            "autonomy": {"enabled": app.state.autonomy["enabled"]},
        }

    @app.post("/api/autonomy")
    def set_autonomy(body: dict = Body(...),
                     x_actor: str | None = Header(default=None)):
        if _actor(x_actor) != Actor.HUMAN:
            raise HTTPException(403, "autonomy is toggled by the human")
        app.state.autonomy["enabled"] = bool(body.get("enabled"))
        return {"enabled": app.state.autonomy["enabled"]}

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

    # ----------------------------------- scheduled verifications (chrono)
    @app.get("/api/followups")
    def followups_list():
        return ctrl.followup_store.snapshot()

    @app.post("/api/followups")
    def followup_schedule(body: dict = Body(...),
                          x_actor: str | None = Header(default=None)):
        _require_human(x_actor)
        return guard(lambda: ctrl.followups.schedule(
            str(body.get("question", "")),
            float(body.get("due_in_days", 1)),
            str(body.get("node_id", "")), Actor.HUMAN))

    @app.post("/api/journal/{decision_id}/explain")
    def explain_decision(decision_id: str):
        """LLM re-elaboration of a decision record for humans: the record
        stays deterministic, the wording is generative (same doctrine as
        deliberation answers)."""
        r = ctrl.journal.rationale(decision_id)
        if r is None:
            raise HTTPException(404, decision_id)
        field_guide = {
            "U/utility": "punteggio con cui le opzioni sono state ordinate: "
                         "contributo agli obiettivi meno costo, rischio e "
                         "costo-opportunità",
            "success_prob": "probabilità di riuscita stimata dal modello, "
                            "calibrata sull'esperienza passata",
            "decision_quality vs outcome_quality":
                "quanto era BUONA la decisione con le informazioni di allora "
                "vs come è ANDATA: possono divergere (sfortuna != errore)",
            "regret": "quanto si sarebbe guadagnato col senno di poi "
                      "scegliendo la migliore alternativa",
            "tainted": "la proposta deriva da contenuti esterni non fidati",
            "verdict": "l'esito del controllo di sicurezza automatico; "
                       "HUMAN_REQUIRED = serviva l'ok del proprietario",
        }
        resp = guard(lambda: ctrl.gateway.ask("explain", {
            "record": r, "field_guide": field_guide,
            "instruction": "spiega questa decisione al proprietario in "
                           "italiano semplice (5-8 frasi): cosa si è deciso "
                           "e perché, contro quali alternative, cosa è "
                           "successo davvero, e la lezione del senno di poi. "
                           "Traduci i numeri in significato, zero gergo."}))
        return {"text": resp.summary}

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

    # ------------------------- external connectors (GUI tab Integrations)
    # live adapters behind the external ports; (re)wired at runtime by the
    # human. Credentials travel once, are held in memory only, and never
    # come back out of this API.
    connectors: dict = {"voice": None, "email": None, "browser": None,
                        "mocks": False,
                        "detail": {"voice": {}, "email": {}, "browser": {}}}

    def _rewire_ports() -> None:
        import os as _os

        from ..tools.external import register_external_ports
        register_external_ports(
            ctrl.registry, voice=connectors["voice"],
            email=connectors["email"], browser=connectors["browser"],
            principal=_os.environ.get("PGDCA_PRINCIPAL", "the owner"),
            enable_mocks=connectors["mocks"])

    def _init_connectors(voice=None, email=None, browser=None,
                         mocks: bool = False) -> None:
        """Called by main() so the startup flags and the GUI stay one truth."""
        connectors.update(voice=voice, email=email, browser=browser,
                          mocks=mocks)

    app.state.init_connectors = _init_connectors
    # apps built without going through main() still get the connection
    # points (disabled placeholders) so the Integrations tab works
    if "voice.call" not in ctrl.registry.names(enabled_only=False):
        _rewire_ports()

    @app.get("/api/connectors")
    def connectors_state():
        out = {}
        for name, tool in (("voice", "voice.call"), ("email", "email.send"),
                           ("sms", "sms.send"), ("browser", "browser.navigate"),
                           ("vault", "vault.pay"),
                           ("identity", "identity.auth_session")):
            try:
                spec = ctrl.registry.spec(tool)
            except KeyError:
                continue
            adapter = connectors.get(name)
            out[name] = {
                "tool": tool,
                "mode": ("real" if adapter is not None
                         else "mock" if spec.enabled else "disabled"),
                "adapter": type(adapter).__name__ if adapter else None,
                "detail": connectors["detail"].get(name, {}),
            }
        return {"connectors": out, "mocks": connectors["mocks"],
                "available": {"voice": "CallAPICall bridge (:8770)",
                              "email": "SMTP/IMAP",
                              "browser": "Playwright/Chromium",
                              "sms": "non ancora implementato",
                              "vault": "non ancora implementato",
                              "identity": "non ancora implementato"}}

    @app.post("/api/connectors")
    def connectors_set(body: dict = Body(...),
                       x_actor: str | None = Header(default=None)):
        """(Re)wire a connector: {"name": "voice|email|browser|mocks",
        "enabled": bool, "config": {...}}. Human-only; hot-swapped."""
        _require_human(x_actor)
        name = str(body.get("name", ""))
        enabled = bool(body.get("enabled"))
        cfg = body.get("config") or {}
        try:
            if name == "mocks":
                connectors["mocks"] = enabled
            elif name == "voice":
                if enabled:
                    from examples.adapters.call_api_call_adapter import (
                        CallAPICallAdapter,
                    )
                    connectors["voice"] = CallAPICallAdapter(
                        base_url=cfg.get("base_url") or None,
                        token=cfg.get("token") or None)
                    connectors["detail"]["voice"] = {
                        "base_url": connectors["voice"].base_url}
                else:
                    connectors["voice"] = None
                    connectors["detail"]["voice"] = {}
            elif name == "email":
                if enabled:
                    from examples.adapters.email_smtp_imap_adapter import (
                        SmtpImapEmailAdapter,
                    )
                    connectors["email"] = SmtpImapEmailAdapter(
                        address=cfg.get("address") or None,
                        password=cfg.get("password") or None,
                        smtp_host=cfg.get("smtp_host") or None,
                        imap_host=cfg.get("imap_host") or None)
                    connectors["detail"]["email"] = {
                        "address": connectors["email"].address,
                        "smtp_host": connectors["email"].smtp_host,
                        "imap_host": connectors["email"].imap_host}
                else:
                    connectors["email"] = None
                    connectors["detail"]["email"] = {}
            elif name == "browser":
                if enabled:
                    from examples.adapters.playwright_browser_adapter import (
                        PlaywrightBrowserAdapter,
                    )
                    old = connectors["browser"]
                    if old is not None:
                        old.close()
                    connectors["browser"] = PlaywrightBrowserAdapter(
                        headless=not cfg.get("show_window", False))
                    connectors["detail"]["browser"] = {
                        "headless": connectors["browser"].headless}
                else:
                    if connectors["browser"] is not None:
                        connectors["browser"].close()
                    connectors["browser"] = None
                    connectors["detail"]["browser"] = {}
            else:
                raise HTTPException(400, f"unknown connector '{name}'")
        except HTTPException:
            raise
        except Exception as exc:  # noqa: BLE001 - misconfig is a 409, not a 500
            raise HTTPException(409, str(exc))
        _rewire_ports()
        ctrl.runtime.emit(Ev.CONFIG_UPDATED,
                          {"changes": {f"connector_{name}":
                                       "on" if enabled else "off"}},
                          Actor.HUMAN)
        return connectors_state()

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
        results = []
        for _ in range(max(1, min(n, 50))):
            with app.state.ctrl_lock:      # non calpestare il runner autonomo
                results.append(ctrl.step().__dict__)
        return {"results": results, "state": ctrl.state.value}

    @app.post("/api/pending/resolve")
    def resolve(body: dict = Body(...),
                x_actor: str | None = Header(default=None),
                x_user: str | None = Header(default=None)):
        actor = _actor(x_actor)
        if actor != Actor.HUMAN:
            raise HTTPException(403, "pending decisions are resolved by the human")
        with app.state.ctrl_lock:
            r = guard(lambda: ctrl.resolve_pending(
                bool(body.get("approve")), _note(body, x_user),
                decision_id=body.get("decision_id") or None))
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
    parser.add_argument("--adapter", choices=["auto", "mock", "llmswitch"],
                        default="auto",
                        help="auto (default): llmswitch when the library is "
                             "installed, mock otherwise. The PROVIDER "
                             "(local engines, API keys, Anthropic, ...) is "
                             "chosen in the llmswitch registry - GUI tab "
                             "LLM or docs/LOCAL_INTEGRATIONS.md. mock = "
                             "deterministic scripted adapter for tests.")
    parser.add_argument("--voice", choices=["none", "callapicall"],
                        default="none",
                        help="voice adapter behind voice.call: callapicall "
                             "drives REAL phone calls through the local "
                             "CallAPICall bridge (:8770) - the Supervisor "
                             "still gates every call as "
                             "EXTERNAL_COMMUNICATION")
    parser.add_argument("--email", choices=["none", "smtp"], default="none",
                        help="email adapter behind email.send/fetch: smtp "
                             "sends REAL email via SMTP/IMAP (configure "
                             "PGDCA_EMAIL_ADDRESS / PGDCA_EMAIL_PASSWORD)")
    parser.add_argument("--browser", choices=["none", "playwright"],
                        default="none",
                        help="browser adapter behind browser.navigate/"
                             "extract: playwright drives a REAL Chromium "
                             "(pip install playwright && playwright install "
                             "chromium); challenges surface to the human")
    parser.add_argument("--mock-ports", action="store_true",
                        help="enable the external ports over their mocks "
                             "(dry-run: voice.call & co. execute without "
                             "touching the real world)")
    parser.add_argument("--empty", action="store_true",
                        help="start with an empty world instead of the toy "
                             "scenario (bring your own goals via the GUI)")
    parser.add_argument("--no-autonomy", action="store_true",
                        help="do not advance by itself (manual stepping "
                             "from the GUI only)")
    parser.add_argument("--no-autoconnect", action="store_true",
                        help="do not self-configure the connectors at boot "
                             "(by default the system probes what exists - "
                             "CallAPICall bridge, email credentials, "
                             "Playwright - and wires it by itself)")
    parser.add_argument("--pace", type=float, default=3.0,
                        help="seconds between autonomous cycles (default 3)")
    args = parser.parse_args()

    adapter = None
    if args.adapter in ("auto", "llmswitch"):
        try:
            # local integration: run from the repo root so `examples` resolves
            from examples.adapters.local_llm_provider_adapter import (
                LocalProviderAdapter,
            )
            adapter = LocalProviderAdapter()
        except ImportError as exc:
            if args.adapter == "llmswitch":
                raise SystemExit(f"llmswitch adapter unavailable: {exc}")
            print(f"[pgdca] llmswitch non disponibile ({exc}): "
                  "uso l'adapter mock deterministico")
    voice = None
    if args.voice == "callapicall":
        from examples.adapters.call_api_call_adapter import CallAPICallAdapter
        voice = CallAPICallAdapter()
    email = None
    if args.email == "smtp":
        from examples.adapters.email_smtp_imap_adapter import (
            SmtpImapEmailAdapter,
        )
        email = SmtpImapEmailAdapter()   # raises with clear text if unset
    browser = None
    if args.browser == "playwright":
        from examples.adapters.playwright_browser_adapter import (
            PlaywrightBrowserAdapter,
        )
        browser = PlaywrightBrowserAdapter()

    # --------------------------- autonomous setup (self-configuration)
    # the system wires by itself whatever is actually available on this
    # machine; the human supervises from the Collegamenti tab, not from
    # command-line flags
    import importlib.util as _ilu
    import os as _os
    if not args.no_autoconnect:
        if voice is None:
            try:
                import requests as _rq
                url = _os.environ.get("CALLBRIDGE_CONTROL_URL",
                                      "http://127.0.0.1:8770").rstrip("/")
                if _rq.get(url + "/health", timeout=2).status_code == 200:
                    from examples.adapters.call_api_call_adapter import (
                        CallAPICallAdapter,
                    )
                    voice = CallAPICallAdapter()
                    print(f"[pgdca] auto-connect: bridge CallAPICall vivo su "
                          f"{url} -> porta voce collegata", flush=True)
            except Exception:  # noqa: BLE001 - bridge spento: nessun dramma
                pass
        if email is None and _os.environ.get("PGDCA_EMAIL_ADDRESS") \
                and _os.environ.get("PGDCA_EMAIL_PASSWORD"):
            from examples.adapters.email_smtp_imap_adapter import (
                SmtpImapEmailAdapter,
            )
            email = SmtpImapEmailAdapter()
            print("[pgdca] auto-connect: credenziali email presenti -> "
                  "porta email collegata", flush=True)
        if browser is None and _ilu.find_spec("playwright") is not None:
            from examples.adapters.playwright_browser_adapter import (
                PlaywrightBrowserAdapter,
            )
            browser = PlaywrightBrowserAdapter()
            print("[pgdca] auto-connect: Playwright installato -> browser "
                  "reale collegato (parte alla prima navigazione)",
                  flush=True)
    ctrl, _env = create(db_path=args.db, adapter=adapter,
                        build=not args.empty)
    # expose the external-world connection points: DISABLED placeholders by
    # default, mocks with --mock-ports (dry-run), real adapters via flags
    import os

    from ..tools.external import register_external_ports
    register_external_ports(ctrl.registry, voice=voice, email=email,
                            browser=browser,
                            principal=os.environ.get("PGDCA_PRINCIPAL",
                                                     "the owner"),
                            enable_mocks=args.mock_ports)
    app = create_app(ctrl)
    # the GUI's Integrations tab reflects and can rewire what the flags set
    app.state.init_connectors(voice=voice, email=email, browser=browser,
                              mocks=args.mock_ports)

    # ------------------------------------------------ autonomous runner
    # the loop advances by itself; the human supervises. It stands still
    # while a decision waits for the human, while paused/stopped, and
    # backs off after an escalation (the thread already awaits an answer).
    import threading
    import time as _time

    if args.no_autonomy:
        app.state.autonomy["enabled"] = False
    app.state.autonomy["interval_s"] = args.pace

    def _runner() -> None:
        auto = app.state.autonomy
        while True:
            try:
                if not auto["enabled"] or ctrl.state.value in (
                        "WAITING_HUMAN", "PAUSED", "STOPPED"):
                    _time.sleep(1.0)
                    continue
                with app.state.ctrl_lock:
                    r = ctrl.step()
                if r.status == "idle":
                    _time.sleep(auto["idle_interval_s"])
                elif r.status == "escalated":
                    _time.sleep(auto["backoff_s"])
                else:
                    _time.sleep(auto["interval_s"])
            except Exception as exc:  # noqa: BLE001 - il runner non muore mai
                print(f"[pgdca] ciclo autonomo fallito: {exc}", flush=True)
                _time.sleep(auto["backoff_s"])

    threading.Thread(target=_runner, name="autonomy", daemon=True).start()
    engine = ("llmswitch (provider scelto nel tab LLM della GUI)"
              if adapter is not None else "mock deterministico (di prova)")
    real = [n for n, a in (("voce/CallAPICall", voice), ("email/SMTP", email),
                           ("browser/Playwright", browser)) if a is not None]
    ports_state = ("REALI: " + ", ".join(real)
                   + ("; il resto sui mock" if args.mock_ports
                      else "; il resto disattivo") if real
                   else "attive sui mock (prova a secco)" if args.mock_ports
                   else "disattive")
    print(f"""
PGDCA avviato.
  Console web:   http://127.0.0.1:{args.port}   (apri questa pagina)
  Motore LLM:    {engine}
  Mondo:         {"vuoto - aggiungi i tuoi goal dal tab Graph"
                  if args.empty else "scenario di prova (montagna)"}
  Memoria:       {"usa e getta (:memory:)" if args.db == ":memory:"
                  else args.db + " (persistente: riprende da dove era)"}
  Porte esterne: {ports_state}
  Autonomia:     {"SPENTA (passi manuali dalla GUI)" if args.no_autonomy
                  else f"attiva - lavora da solo (un ciclo ogni ~{args.pace:g}s),"
                       " si ferma quando serve una tua decisione"}
Ctrl+C per fermare.""", flush=True)
    # without a graceful-shutdown cap, Ctrl+C hangs on Windows: the GUI's
    # open SSE stream (/api/events/stream) never closes by itself and
    # uvicorn waits for it forever
    uvicorn.run(app, host="127.0.0.1", port=args.port, log_level="warning",
                timeout_graceful_shutdown=3)


if __name__ == "__main__":  # pragma: no cover
    main()
