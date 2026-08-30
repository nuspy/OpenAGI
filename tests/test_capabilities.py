"""M28: imported skill packages and MCP servers, with security gates."""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

from pgdca.events import Actor, Ev
from pgdca.tools.skills import SkillValidationError, load_skill_package
from tests.conftest import events_of

REPO = Path(__file__).resolve().parent.parent
SKILL_DIR = REPO / "examples" / "skills" / "procurement-discipline"
MCP_CMD = [sys.executable, str(REPO / "examples" / "mcp" / "toy_market_server.py")]


# ---------------------------------------------------------------- skills
def test_skill_package_validation(tmp_path):
    with pytest.raises(SkillValidationError):
        load_skill_package(tmp_path)  # empty dir
    s = load_skill_package(SKILL_DIR)
    assert s["name"] == "procurement-discipline"
    assert s["trust"] == "untrusted" and s["provenance"] == "imported"


def test_skill_import_and_progressive_disclosure(ctrl_env):
    ctrl, _ = ctrl_env
    ctrl.import_skill(str(SKILL_DIR), Actor.HUMAN)
    assert events_of(ctrl, Ev.SKILL_IMPORTED.value)
    ctx = ctrl._build_context()
    assert any(s["name"] == "procurement-discipline" for s in ctx["skills"])
    ctrl.step()  # the mock notes the applied skills in its assumptions
    resp = [e for e in events_of(ctrl, Ev.LLM_RESPONSE.value)
            if e.payload["raw"].get("role") == "hypotheses"]
    assert any("procurement-discipline" in a
               for a in resp[-1].payload["raw"].get("assumptions", []))
    # disabling removes it from the briefing
    ctrl.set_skill_enabled("procurement-discipline", False, Actor.HUMAN)
    assert not ctrl._build_context()["skills"]


def test_risky_skill_import_by_system_needs_human(ctrl_env):
    ctrl, _ = ctrl_env
    risky = {"name": "outreach", "description": "sends messages",
             "version": "1", "risk_class": "EXTERNAL_COMMUNICATION",
             "triggers": ["email"], "instructions": "...",
             "provenance": "imported", "trust": "untrusted"}
    s = ctrl.capabilities.import_skill(risky, Actor.SYSTEM)
    assert s["enabled"] is False and s["status"] == "PENDING_HUMAN"
    with pytest.raises(PermissionError):
        ctrl.set_skill_enabled("outreach", True, Actor.SYSTEM)
    ctrl.set_skill_enabled("outreach", True, Actor.HUMAN)
    assert ctrl.capability_store.skills["outreach"]["enabled"] is True


# ------------------------------------------------------------------- MCP
@pytest.fixture
def mcp_cleanup(ctrl_env):
    ctrl, _ = ctrl_env
    yield ctrl
    ctrl.capabilities.mcp.close_all()


def test_mcp_import_by_human_registers_and_executes(mcp_cleanup):
    ctrl = mcp_cleanup
    ctrl.import_mcp_server("market", MCP_CMD, Actor.HUMAN)
    assert events_of(ctrl, Ev.MCP_SERVER_REGISTERED.value)
    assert "market.lookup_price" in ctrl.registry.names()
    spec = ctrl.registry.spec("market.lookup_price")
    assert spec.risk_class == "EXTERNAL_COMMUNICATION"   # restrictive default
    assert spec.description_trust == "untrusted"
    r = ctrl.registry.execute("market.add", {"a": 2, "b": 3})
    assert r.status == "ok" and r.observation["text"] == "5"
    assert r.observation["trust"] == "untrusted"          # output is data
    r2 = ctrl.registry.execute("market.lookup_price", {"factor_id": "boots"})
    assert r2.status == "ok" and "400" in r2.observation["text"]


def test_mcp_import_by_system_is_disabled_until_approved(mcp_cleanup):
    ctrl = mcp_cleanup
    ctrl.import_mcp_server("market", MCP_CMD, Actor.SYSTEM)
    r = ctrl.registry.execute("market.add", {"a": 1, "b": 1})
    assert r.status == "failed" and "disabled" in r.error
    with pytest.raises(PermissionError):
        ctrl.approve_mcp_server("market", Actor.SYSTEM)
    ctrl.approve_mcp_server("market", Actor.HUMAN)
    assert ctrl.registry.execute("market.add", {"a": 1, "b": 1}).status == "ok"


def test_mcp_registry_survives_recovery(tmp_path):
    from pgdca.scenario.toy import create
    db = str(tmp_path / "mcp.db")
    ctrl1, _ = create(db_path=db)
    ctrl1.import_mcp_server("market", MCP_CMD, Actor.HUMAN)
    ctrl1.capabilities.mcp.close_all()
    del ctrl1

    ctrl2, _ = create(db_path=db)
    try:
        assert "market.add" in ctrl2.registry.names()      # re-registered
        r = ctrl2.registry.execute("market.add", {"a": 4, "b": 5})
        assert r.status == "ok" and r.observation["text"] == "9"  # lazy reconnect
    finally:
        ctrl2.capabilities.mcp.close_all()
