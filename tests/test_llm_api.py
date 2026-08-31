"""LLM provider selection API (GUI tab "LLM").

These tests need the local llmswitch library (they skip elsewhere) but
never touch the owner's real registry: the registry root is redirected
to a pytest tmp dir via the environment.
"""
from __future__ import annotations

import importlib.util

import pytest

fastapi = pytest.importorskip("fastapi")
if importlib.util.find_spec("llmswitch") is None:
    pytest.skip("llmswitch not installed (local-only integration)",
                allow_module_level=True)

from fastapi.testclient import TestClient  # noqa: E402

from pgdca.api.server import create_app  # noqa: E402
from pgdca.scenario.toy import create  # noqa: E402


@pytest.fixture
def client(tmp_path, monkeypatch):
    # the llmswitch registry resolves under LOCALAPPDATA/XDG_CONFIG_HOME:
    # point both at a sandbox so tests never write the real registry
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    monkeypatch.setenv("PGDCA_LLMSWITCH_APP", "pgdca-test")
    ctrl, _ = create()
    return TestClient(create_app(ctrl)), ctrl


def test_llm_info_reports_adapter_and_empty_registry(client):
    c, _ = client
    d = c.get("/api/llm").json()
    assert d["adapter"] == "MockLlmAdapter"
    assert d["llmswitch"]["available"] is True
    assert d["llmswitch"]["providers"] == []
    assert "pgdca-test" in d["llmswitch"]["registry_path"]


def test_provider_crud_assign_and_no_secret_leak(client):
    c, _ = client
    r = c.post("/api/llm/providers",
               json={"type": "openai_compat", "name": "wall",
                     "base_url": "http://127.0.0.1:9/v1",
                     "model": "m1", "api_key": "sk-secret"},
               headers={"X-Actor": "human"})
    assert r.status_code == 200
    pid = r.json()["id"]
    d = c.get("/api/llm").json()["llmswitch"]
    prov = next(p for p in d["providers"] if p["id"] == pid)
    assert prov["has_key"] is True
    assert "sk-secret" not in c.get("/api/llm").text   # keys never cross
    r = c.post("/api/llm/assign",
               json={"consumer": "chat", "provider_id": pid},
               headers={"X-Actor": "human"})
    assert r.json()["assignments"]["chat"] == pid
    r = c.post(f"/api/llm/providers/{pid}/remove",
               headers={"X-Actor": "human"})
    assert r.status_code == 200
    d = c.get("/api/llm").json()["llmswitch"]
    assert d["providers"] == [] and d["assignments"] == {}


def test_connectors_wire_and_unwire_at_runtime(client, monkeypatch):
    c, ctrl = client
    monkeypatch.setenv("PGDCA_EMAIL_ADDRESS", "me@example.test")
    monkeypatch.setenv("PGDCA_EMAIL_PASSWORD", "app-pass")
    d = c.get("/api/connectors").json()
    assert d["connectors"]["email"]["mode"] == "disabled"
    assert c.post("/api/connectors", json={"name": "email", "enabled": True},
                  headers={"X-Actor": "system"}).status_code == 403
    r = c.post("/api/connectors", json={"name": "email", "enabled": True},
               headers={"X-Actor": "human"})
    assert r.status_code == 200
    assert r.json()["connectors"]["email"]["mode"] == "real"
    assert ctrl.registry.spec("email.send").enabled is True
    assert "app-pass" not in r.text            # credentials never come back
    r = c.post("/api/connectors", json={"name": "mocks", "enabled": True},
               headers={"X-Actor": "human"})
    assert r.json()["connectors"]["voice"]["mode"] == "mock"
    r = c.post("/api/connectors", json={"name": "email", "enabled": False},
               headers={"X-Actor": "human"})
    assert r.json()["connectors"]["email"]["mode"] == "mock"  # mocks still on


def test_adapter_switch_is_human_only_and_audited(client):
    c, ctrl = client
    r = c.post("/api/llm/adapter", json={"type": "llmswitch"},
               headers={"X-Actor": "system"})
    assert r.status_code == 403
    r = c.post("/api/llm/adapter", json={"type": "llmswitch"},
               headers={"X-Actor": "human"})
    assert r.status_code == 200
    assert type(ctrl.gateway.adapter).__name__ == "LocalProviderAdapter"
    assert any(e.type == "CONFIG_UPDATED"
               and e.payload.get("changes", {}).get("llm_adapter") == "llmswitch"
               for e in ctrl.runtime.events())
    r = c.post("/api/llm/adapter", json={"type": "mock"},
               headers={"X-Actor": "human"})
    assert type(ctrl.gateway.adapter).__name__ == "MockLlmAdapter"
    assert c.post("/api/llm/adapter", json={"type": "nope"},
                  headers={"X-Actor": "human"}).status_code == 400
