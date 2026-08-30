"""Capability store: imported skills and MCP servers as projections.

Import security (M10/M28): imports by the system identity land disabled
(PENDING_HUMAN) when their risk class reaches EXTERNAL_COMMUNICATION;
human imports enable immediately. Enabling is itself an auditable
event; tool adapters register into the ToolRegistry with the enabled
flag mirrored, so a disabled capability cannot execute.
"""
from __future__ import annotations

from ..events import Actor, Ev, Event
from ..security.supervisor import RISK_ORDER, RiskClass
from .mcp_client import McpManager
from .provenance import digest_files, pin_command, skill_package_digest
from .registry import ToolRegistry, ToolResult, ToolSpec

RISKY = RISK_ORDER[RiskClass.EXTERNAL_COMMUNICATION.value]


class CapabilityStore:
    """Projection over skill/MCP events."""

    def __init__(self):
        self.skills: dict[str, dict] = {}
        self.mcp_servers: dict[str, dict] = {}

    def apply(self, ev: Event) -> None:
        t, p = ev.type, ev.payload
        if t == Ev.SKILL_IMPORTED.value:
            s = p["skill"]
            self.skills[s["name"]] = s
        elif t == Ev.SKILL_UPDATED.value:
            s = self.skills.get(p["name"])
            if s is not None:
                s.update(p.get("changes", {}))
        elif t == Ev.SKILL_RETIRED.value:
            self.skills.pop(p["name"], None)
        elif t == Ev.MCP_SERVER_REGISTERED.value:
            self.mcp_servers[p["server_id"]] = {
                "server_id": p["server_id"], "command": p["command"],
                "tools": p["tools"], "enabled": p["enabled"],
                "provenance": p.get("provenance", "import"),
                "pin": p.get("pin")}
        elif t == Ev.MCP_SERVER_UPDATED.value:
            s = self.mcp_servers.get(p["server_id"])
            if s is not None:
                s.update(p.get("changes", {}))

    def enabled_skills(self) -> list[dict]:
        return sorted((s for s in self.skills.values() if s.get("enabled")),
                      key=lambda s: s["name"])

    def snapshot(self) -> dict:
        return {"skills": sorted(self.skills.values(), key=lambda s: s["name"]),
                "mcp_servers": sorted(self.mcp_servers.values(),
                                      key=lambda s: s["server_id"])}


class CapabilityManager:
    """Commands: import/enable skills and MCP servers, wire the registry."""

    def __init__(self, runtime, store: CapabilityStore, registry: ToolRegistry,
                 mcp: McpManager | None = None, config=None):
        self.runtime = runtime
        self.store = store
        self.registry = registry
        if mcp is None:
            profile = None
            if config is not None:
                from .sandbox import SandboxProfile
                profile = SandboxProfile(
                    cpu_seconds=config.sandbox_cpu_seconds,
                    memory_bytes=config.sandbox_memory_bytes,
                    wall_seconds=config.sandbox_wall_seconds)
            mcp = McpManager(profile=profile)
        self.mcp = mcp

    # ------------------------------------------------------------- skills
    def import_skill(self, skill: dict, actor: Actor) -> dict:
        risky = RISK_ORDER[skill.get("risk_class", "READ_ONLY")] >= RISKY
        enabled = actor == Actor.HUMAN or not risky
        skill = dict(skill, enabled=enabled,
                     status="ACTIVE" if enabled else "PENDING_HUMAN")
        self.runtime.emit(Ev.SKILL_IMPORTED, {"skill": skill}, actor)
        return skill

    def set_skill_enabled(self, name: str, enabled: bool, actor: Actor) -> None:
        s = self.store.skills.get(name)
        if s is None:
            raise KeyError(name)
        risky = RISK_ORDER[s.get("risk_class", "READ_ONLY")] >= RISKY
        if enabled and risky and actor != Actor.HUMAN:
            raise PermissionError(
                "enabling a skill at EXTERNAL_COMMUNICATION or above requires the human")
        self.runtime.emit(Ev.SKILL_UPDATED,
                          {"name": name,
                           "changes": {"enabled": enabled,
                                       "status": "ACTIVE" if enabled else "DISABLED"}},
                          actor)

    # ---------------------------------------------------------------- MCP
    def import_mcp_server(self, server_id: str, command: list[str],
                          actor: Actor) -> dict:
        """Connect, enumerate tools, register them at a restrictive default
        risk class. System imports stay disabled until human approval."""
        conn = self.mcp.connection(server_id, command)
        tools = conn.list_tools()
        enabled = actor == Actor.HUMAN
        tool_meta = [{"name": t.name, "description": t.description,
                      "input_schema": t.input_schema} for t in tools]
        self.runtime.emit(Ev.MCP_SERVER_REGISTERED,
                          {"server_id": server_id, "command": command,
                           "tools": tool_meta, "enabled": enabled,
                           "provenance": f"mcp_import:{actor.value}",
                           "pin": pin_command(command)},
                          actor)
        for t in tool_meta:
            self.runtime.emit(Ev.TOOL_REGISTERED,
                              {"name": f"{server_id}.{t['name']}",
                               "risk_class": RiskClass.EXTERNAL_COMMUNICATION.value,
                               "provenance": f"mcp:{server_id}",
                               "enabled": enabled,
                               "description_trust": "untrusted"},
                              actor)
        self._register_server_tools(server_id, command, tool_meta, enabled)
        return self.store.mcp_servers[server_id]

    def approve_mcp_server(self, server_id: str, actor: Actor) -> None:
        if actor != Actor.HUMAN:
            raise PermissionError("only the human identity approves MCP servers")
        s = self.store.mcp_servers.get(server_id)
        if s is None:
            raise KeyError(server_id)
        self.runtime.emit(Ev.MCP_SERVER_UPDATED,
                          {"server_id": server_id, "changes": {"enabled": True}},
                          actor)
        for t in s["tools"]:
            self.registry.set_enabled(f"{server_id}.{t['name']}", True)

    def disable_mcp_server(self, server_id: str, actor: Actor) -> None:
        s = self.store.mcp_servers.get(server_id)
        if s is None:
            raise KeyError(server_id)
        self.runtime.emit(Ev.MCP_SERVER_UPDATED,
                          {"server_id": server_id, "changes": {"enabled": False}},
                          actor)
        for t in s["tools"]:
            self.registry.set_enabled(f"{server_id}.{t['name']}", False)

    # ----------------------------------------------------------- wiring
    def _register_server_tools(self, server_id: str, command: list[str],
                               tools: list[dict], enabled: bool) -> None:
        for t in tools:
            full_name = f"{server_id}.{t['name']}"

            def make_adapter(tool_name=t["name"], sid=server_id, cmd=list(command)):
                def adapter(params: dict) -> ToolResult:
                    if params.get("__conformance__"):
                        return ToolResult(status="failed",
                                          error="conformance probe (no connection)")
                    try:
                        conn = self.mcp.connection(sid, cmd)
                        r = conn.call_tool(tool_name, params)
                    except Exception as exc:  # noqa: BLE001
                        return ToolResult(status="failed", error=repr(exc))
                    if r["is_error"]:
                        return ToolResult(status="failed", error=r["text"] or "MCP error")
                    return ToolResult(status="ok",
                                      observation={"text": r["text"],
                                                   "trust": "untrusted"})
                return adapter

            self.registry.register(
                ToolSpec(name=full_name,
                         risk_class=RiskClass.EXTERNAL_COMMUNICATION.value,
                         description=t.get("description", ""),
                         provenance=f"mcp:{server_id}",
                         enabled=enabled,
                         description_trust="untrusted"),
                make_adapter())

    def set_tool_enabled(self, name: str, enabled: bool, actor: Actor) -> None:
        """Human-gated promotion: enabling any tool at
        EXTERNAL_COMMUNICATION or above is a human decision (M10)."""
        spec = next((s for s in self.registry.specs() if s.name == name), None)
        if spec is None:
            raise KeyError(name)
        if (enabled and RISK_ORDER.get(spec.risk_class, 0) >= RISKY
                and actor != Actor.HUMAN):
            raise PermissionError("enabling a tool at EXTERNAL_COMMUNICATION "
                                  "or above requires the human")
        self.runtime.emit(Ev.TOOL_UPDATED,
                          {"name": name, "changes": {"enabled": enabled}},
                          actor)
        self.registry.set_enabled(name, enabled)

    # ------------------------------------------------- provenance (M10)
    def verify_all(self) -> list[dict]:
        """Re-verify every pinned capability against its import-time
        digest. What was reviewed is what runs: a mismatch (or a missing
        source) quarantines the capability - disabled plus an auditable
        CAPABILITY_QUARANTINED event - never a silent re-import."""
        quarantined: list[dict] = []
        for s in list(self.store.skills.values()):
            src, expected = s.get("source_path"), s.get("digest")
            if not src or not expected:
                continue
            try:
                current = skill_package_digest(src)
            except OSError:
                current = None
            if current != expected:
                self._quarantine("skill", s["name"], expected, current)
                quarantined.append({"kind": "skill", "name": s["name"]})
        for m in list(self.store.mcp_servers.values()):
            pin = m.get("pin")
            if not pin or not pin.get("digest"):
                continue
            try:
                current = digest_files(*pin["paths"])
            except OSError:
                current = None
            if current != pin["digest"]:
                self._quarantine("mcp_server", m["server_id"],
                                 pin["digest"], current)
                quarantined.append({"kind": "mcp_server",
                                    "name": m["server_id"]})
        return quarantined

    def _quarantine(self, kind: str, name: str, expected: str,
                    found: str | None) -> None:
        changes = {"enabled": False, "status": "QUARANTINED",
                   "quarantine": "content changed since import "
                                 "(digest mismatch)"}
        if kind == "skill":
            self.runtime.emit(Ev.SKILL_UPDATED,
                              {"name": name, "changes": changes},
                              Actor.SUPERVISOR)
        else:
            self.runtime.emit(Ev.MCP_SERVER_UPDATED,
                              {"server_id": name, "changes": changes},
                              Actor.SUPERVISOR)
            server = self.store.mcp_servers.get(name, {})
            for t in server.get("tools", []):
                self.registry.set_enabled(f"{name}.{t['name']}", False)
        self.runtime.emit(Ev.CAPABILITY_QUARANTINED,
                          {"kind": kind, "name": name,
                           "expected_digest": expected,
                           "found_digest": found}, Actor.SUPERVISOR)

    def restore_registry(self) -> None:
        """After recovery: re-register MCP tools from the projection with
        lazy connections, then re-verify pinned content - a capability
        whose code changed across the restart comes back quarantined,
        not armed."""
        for s in self.store.mcp_servers.values():
            self._register_server_tools(s["server_id"], s["command"],
                                        s["tools"], s["enabled"])
        self.verify_all()
