"""API layer: commands carry identity; store-level guarantees hold over HTTP."""
from __future__ import annotations

import pytest

fastapi = pytest.importorskip("fastapi")
from fastapi.testclient import TestClient  # noqa: E402

from pgdca.api.server import create_app  # noqa: E402
from pgdca.scenario.toy import create  # noqa: E402


@pytest.fixture
def client():
    ctrl, _ = create()
    return TestClient(create_app(ctrl)), ctrl


def test_state_graph_and_step(client):
    c, ctrl = client
    assert c.get("/api/state").json()["state"] == "INITIALIZING"
    g = c.get("/api/graph").json()
    assert any(n["id"] == "boots" for n in g["nodes"])
    r = c.post("/api/step", json={"n": 2})
    assert r.status_code == 200 and ctrl.cycle >= 1


def test_tier1_guardrail_not_writable_via_api_as_system(client):
    c, _ = client
    body = {"description": "sneaky", "tier": 1,
            "rule": {"kind": "behavior_block", "blocked": ["x"]}}
    r = c.post("/api/guardrails", json=body, headers={"X-Actor": "system"})
    assert r.status_code == 403
    r2 = c.post("/api/guardrails", json=body, headers={"X-Actor": "human"})
    assert r2.status_code == 200


def test_budget_ratchet_via_api(client):
    c, _ = client
    r = c.post("/api/budget", json={"name": "money", "limit": 9999},
               headers={"X-Actor": "system"})
    assert r.status_code == 403
    r2 = c.post("/api/budget", json={"name": "money", "limit": 600})
    assert r2.status_code == 200


def test_pending_flow_via_api(client):
    c, ctrl = client
    # drive until the boots purchase waits for the human
    for _ in range(20):
        st = c.post("/api/step", json={"n": 1}).json()["state"]
        if st == "WAITING_HUMAN":
            break
    assert c.get("/api/state").json()["pending"] is not None
    inbox = c.get("/api/inbox").json()
    assert inbox["pending"]
    r = c.post("/api/pending/resolve", json={"approve": True, "note": "ok"})
    assert r.status_code == 200
    assert ctrl.budgets.snapshot()["money"]["spent"] >= 400


def test_node_edit_and_deliberation(client):
    c, ctrl = client
    r = c.post("/api/graph/nodes/boots", json={"props": {"importance": 0.7}})
    assert r.status_code == 200
    assert ctrl.graph.node("boots")["props"]["importance"] == 0.7
    r2 = c.post("/api/graph/nodes/boots", json={"props": {"importance": 0.7}},
                headers={"X-Actor": "system"})
    assert r2.status_code == 403
    h = c.get("/api/nodes/boots/decisions")
    assert h.status_code == 200 and "node" in h.json()
    d = c.post("/api/deliberations", json={"subject_kind": "node",
                                           "subject_id": "boots",
                                           "question": "why?"})
    assert d.status_code == 200
    th = d.json()
    assert th["messages"][0]["author"] == "human"
    assert th["messages"][1]["author"] == "system"
    assert "boots" in th["messages"][1]["text"]
    sysopen = c.post("/api/deliberations", json={"subject_kind": "node",
                                                 "subject_id": "boots",
                                                 "question": "hi"},
                     headers={"X-Actor": "system"})
    assert sysopen.status_code == 403
    rr = c.post(f"/api/deliberations/{th['id']}/reply", json={"text": "ok then"})
    assert rr.status_code == 200 and len(rr.json()["messages"]) == 4
    rs = c.post(f"/api/deliberations/{th['id']}/resolve",
                json={"outcome": "confirmed", "note": "fine"})
    assert rs.status_code == 200 and rs.json()["status"] == "RESOLVED"
    again = c.post(f"/api/deliberations/{th['id']}/resolve",
                   json={"outcome": "confirmed"})
    assert again.status_code == 409
    assert c.get("/api/deliberations").json()[0]["id"] == th["id"]


def test_control_and_ui(client):
    c, _ = client
    assert c.post("/api/control/pause").json()["state"] == "PAUSED"
    assert c.post("/api/control/resume").status_code == 200
    home = c.get("/")
    assert home.status_code == 200 and b"PGDCA" in home.content
