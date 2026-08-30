"""Phase 7: runtime config editing, goal ratification over the API,
operator identity in notes, external-content attention hygiene."""
from __future__ import annotations

import pytest

from pgdca.events import Actor, Ev
from pgdca.scenario.toy import ADVERT_TEXT, create
from tests.conftest import events_of

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from pgdca.api.server import create_app  # noqa: E402


@pytest.fixture
def client():
    ctrl, _ = create()
    return TestClient(create_app(ctrl)), ctrl


# ------------------------------------------------------------- config
def test_config_is_human_editable_only(ctrl_env):
    ctrl, _ = ctrl_env
    with pytest.raises(PermissionError):
        ctrl.update_config({"taint_window_cycles": 0}, Actor.SYSTEM)
    applied = ctrl.update_config({"taint_window_cycles": "5",
                                  "strategy_adherence_bonus": 0.1},
                                 Actor.HUMAN)
    assert applied == {"taint_window_cycles": 5,
                       "strategy_adherence_bonus": 0.1}
    assert ctrl.config.taint_window_cycles == 5          # coerced to int
    assert ctrl.taint.config.taint_window_cycles == 5    # shared reference
    assert events_of(ctrl, Ev.CONFIG_UPDATED.value)


def test_unknown_or_invalid_config_fields_are_rejected(ctrl_env):
    ctrl, _ = ctrl_env
    with pytest.raises(KeyError):
        ctrl.update_config({"no_such_field": 1}, Actor.HUMAN)
    with pytest.raises(ValueError):
        ctrl.update_config({"taint_window_cycles": "many"}, Actor.HUMAN)
    with pytest.raises(ValueError):
        ctrl.update_config({"role_models": "not-an-object"}, Actor.HUMAN)
    assert ctrl.config.taint_window_cycles == 2   # nothing applied


def test_config_changes_survive_recovery(tmp_path):
    db = str(tmp_path / "cfg.db")
    ctrl, _ = create(db_path=db)
    ctrl.update_config({"macro_interval_cycles": 25}, Actor.HUMAN)
    del ctrl
    ctrl2, _ = create(db_path=db)
    assert ctrl2.config.macro_interval_cycles == 25


def test_config_api(client):
    c, ctrl = client
    cfg = c.get("/api/config").json()
    assert cfg["taint_window_cycles"] == 2
    r = c.post("/api/config", json={"changes": {"taint_window_cycles": 4}},
               headers={"X-Actor": "system"})
    assert r.status_code == 403
    r2 = c.post("/api/config", json={"changes": {"taint_window_cycles": 4}})
    assert r2.status_code == 200 and ctrl.config.taint_window_cycles == 4
    assert c.post("/api/config",
                  json={"changes": {"nope": 1}}).status_code == 404


# ---------------------------------------------------- goal ratification
def test_goal_proposal_and_ratification_via_api(client):
    c, ctrl = client
    r = c.post("/api/goals", json={"kind": "PERSISTENT_GOAL",
                                   "label": "Learn to climb",
                                   "priority": 0.7})
    gid = r.json()["id"]
    assert ctrl.graph.node(gid)["status"] == "PROPOSED"
    deny = c.post(f"/api/goals/{gid}/ratify", headers={"X-Actor": "system"})
    assert deny.status_code == 403
    ok = c.post(f"/api/goals/{gid}/ratify")
    assert ok.status_code == 200
    assert ctrl.graph.node(gid)["status"] == "ACTIVE"


# ---------------------------------------------------- operator identity
def test_operator_name_is_stamped_into_notes(client):
    c, ctrl = client
    for _ in range(20):
        if c.post("/api/step", json={"n": 1}).json()["state"] == "WAITING_HUMAN":
            break
    r = c.post("/api/pending/resolve", json={"approve": True, "note": "ok"},
               headers={"X-User": "alice"})
    assert r.status_code == 200
    override = next(r_["override"] for r_ in ctrl.journal.records.values()
                    if r_.get("override"))
    assert override["note"] == "ok [by alice]"


# ----------------------------------------------------- context hygiene
def test_old_external_content_leaves_the_briefing_but_not_the_log(ctrl_env):
    ctrl, _ = ctrl_env
    ctrl.update_config({"external_content_context_cycles": 2}, Actor.HUMAN)
    ctrl.step()
    cid = ctrl.ingest_external(ADVERT_TEXT, source="advert-site")
    ctrl.step()
    assert any(c["id"] == cid
               for c in ctrl._build_context()["external_content"])
    for _ in range(4):
        r = ctrl.step()
        if r.status == "waiting_human":
            ctrl.resolve_pending(False, "deny for the hygiene test")
    assert ctrl.cycle - 1 > 2
    assert not any(c["id"] == cid
                   for c in ctrl._build_context()["external_content"])
    # the event log never forgets: audit and replay keep the full record
    assert any(e.payload.get("content_id") == cid
               for e in events_of(ctrl, Ev.CONTENT_INGESTED.value))
    assert any(c["id"] == cid for c in ctrl.taint.contents)
