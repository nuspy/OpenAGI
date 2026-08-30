#!/usr/bin/env python3
"""A tiny MCP server (stdio, newline-delimited JSON-RPC) for tests/demo.

Exposes two tools: `lookup_price` (canned market data) and `add`.
"""
from __future__ import annotations

import json
import sys

PRICES = {"boots": 400.0, "helmet": 80.0, "bars": 20.0, "fruit": 2.0,
          "rope": 35.0}

TOOLS = [
    {"name": "lookup_price",
     "description": "Look up the market price of an item",
     "inputSchema": {"type": "object",
                     "properties": {"factor_id": {"type": "string"}},
                     "required": ["factor_id"]}},
    {"name": "add",
     "description": "Add two numbers",
     "inputSchema": {"type": "object",
                     "properties": {"a": {"type": "number"},
                                    "b": {"type": "number"}},
                     "required": ["a", "b"]}},
]


def reply(msg_id, result):
    sys.stdout.write(json.dumps({"jsonrpc": "2.0", "id": msg_id,
                                 "result": result}) + "\n")
    sys.stdout.flush()


def text_result(text, is_error=False):
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        method = msg.get("method")
        msg_id = msg.get("id")
        if method == "initialize":
            reply(msg_id, {"protocolVersion": msg["params"].get("protocolVersion"),
                           "capabilities": {"tools": {}},
                           "serverInfo": {"name": "toy-market", "version": "1.0.0"}})
        elif method == "notifications/initialized":
            continue
        elif method == "tools/list":
            reply(msg_id, {"tools": TOOLS})
        elif method == "tools/call":
            params = msg.get("params", {})
            name = params.get("name")
            args = params.get("arguments", {})
            if name == "lookup_price":
                fid = args.get("factor_id")
                if fid in PRICES:
                    reply(msg_id, text_result(json.dumps(
                        {"factor_id": fid, "unit_cost": PRICES[fid]})))
                else:
                    reply(msg_id, text_result(f"unknown item '{fid}'", True))
            elif name == "add":
                reply(msg_id, text_result(str(args.get("a", 0) + args.get("b", 0))))
            else:
                reply(msg_id, text_result(f"unknown tool '{name}'", True))
        elif msg_id is not None:
            reply(msg_id, {})


if __name__ == "__main__":
    main()
