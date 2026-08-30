"""Minimal MCP (Model Context Protocol) client over stdio (M28).

The tool registry acts as an MCP client: on import it launches the
server process, performs the initialize handshake, enumerates tools and
maps them into the registry with a restrictive default risk class.
Descriptions are untrusted data (description poisoning is a known
attack on MCP-style ecosystems); execution goes through the same
supervisor gates as every other tool.

This is a deliberately small, dependency-free stdio client (newline-
delimited JSON-RPC 2.0). Swapping in the official SDK later is an
adapter change behind the same port. Server processes launch inside
the M10 sandbox: resource limits, whitelisted environment (no
credential leakage into acquired code), isolated working directory,
process-group termination.
"""
from __future__ import annotations

import json
import select
import subprocess
from dataclasses import dataclass

from .sandbox import SandboxProfile, kill_sandboxed, sandbox_popen

PROTOCOL_VERSION = "2025-06-18"


class McpError(RuntimeError):
    pass


@dataclass
class McpTool:
    name: str
    description: str
    input_schema: dict


class McpConnection:
    def __init__(self, command: list[str], timeout: float = 10.0,
                 profile: SandboxProfile | None = None):
        self.command = command
        self.timeout = timeout
        self.profile = profile or SandboxProfile()
        self._proc: subprocess.Popen | None = None
        self._next_id = 0

    # ------------------------------------------------------------ plumbing
    def _ensure(self) -> subprocess.Popen:
        if self._proc is None or self._proc.poll() is not None:
            self._proc = sandbox_popen(
                self.command, self.profile,
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL, text=True, bufsize=1)
            self._handshake()
        return self._proc

    def _send(self, msg: dict) -> None:
        proc = self._proc
        assert proc and proc.stdin
        proc.stdin.write(json.dumps(msg) + "\n")
        proc.stdin.flush()

    def _read_response(self, want_id: int) -> dict:
        proc = self._proc
        assert proc and proc.stdout
        while True:
            ready, _, _ = select.select([proc.stdout], [], [], self.timeout)
            if not ready:
                raise McpError(f"MCP server timed out after {self.timeout}s")
            line = proc.stdout.readline()
            if not line:
                raise McpError("MCP server closed its stdout")
            try:
                msg = json.loads(line)
            except json.JSONDecodeError:
                continue  # tolerate stray output lines
            if msg.get("id") == want_id:
                if "error" in msg:
                    raise McpError(str(msg["error"]))
                return msg.get("result", {})
            # notifications / unrelated ids are skipped

    def _request(self, method: str, params: dict | None = None) -> dict:
        self._ensure()
        self._next_id += 1
        rid = self._next_id
        self._send({"jsonrpc": "2.0", "id": rid, "method": method,
                    "params": params or {}})
        return self._read_response(rid)

    def _handshake(self) -> None:
        self._next_id += 1
        rid = self._next_id
        self._send({"jsonrpc": "2.0", "id": rid, "method": "initialize",
                    "params": {"protocolVersion": PROTOCOL_VERSION,
                               "capabilities": {},
                               "clientInfo": {"name": "pgdca", "version": "0.1.0"}}})
        self._read_response(rid)
        self._send({"jsonrpc": "2.0", "method": "notifications/initialized",
                    "params": {}})

    # ------------------------------------------------------------- surface
    def list_tools(self) -> list[McpTool]:
        result = self._request("tools/list")
        return [McpTool(name=t["name"], description=t.get("description", ""),
                        input_schema=t.get("inputSchema", {}))
                for t in result.get("tools", [])]

    def call_tool(self, name: str, arguments: dict) -> dict:
        result = self._request("tools/call", {"name": name, "arguments": arguments})
        text = "".join(c.get("text", "") for c in result.get("content", [])
                       if c.get("type") == "text")
        return {"is_error": bool(result.get("isError")), "text": text,
                "raw": result}

    def close(self) -> None:
        if self._proc is not None:
            kill_sandboxed(self._proc)
        self._proc = None


class McpManager:
    """Holds (lazily connected) MCP server connections by server id."""

    def __init__(self, profile: SandboxProfile | None = None):
        self.profile = profile
        self._conns: dict[str, McpConnection] = {}

    def connection(self, server_id: str, command: list[str]) -> McpConnection:
        conn = self._conns.get(server_id)
        if conn is None:
            conn = McpConnection(command, profile=self.profile)
            self._conns[server_id] = conn
        return conn

    def close_all(self) -> None:
        for c in self._conns.values():
            c.close()
        self._conns.clear()
