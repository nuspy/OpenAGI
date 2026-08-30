"""CallAPICall adapter behind VoiceCallPort (fake bridge, no network).

The real bridge dials REAL phone numbers, so its conformance suite runs
only manually against an owner-supplied test number. These tests exercise
the adapter over an in-memory fake of the /external REST API
(call-bridge/callbridge/api_external.py semantics).
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from examples.adapters.call_api_call_adapter import CallAPICallAdapter  # noqa: E402
from pgdca.ports import voice as voice_port  # noqa: E402
from pgdca.tools.external import register_external_ports  # noqa: E402
from pgdca.tools.registry import ToolRegistry  # noqa: E402


class FakeBridge:
    """In-memory stand-in for the CallAPICall /external REST API."""

    def __init__(self, replies=("Pronto, chi parla?",)):
        self.replies = list(replies)
        self.calls: dict[str, dict] = {}
        self.requests: list[tuple[str, str, dict | None]] = []
        self._n = 0

    def _reply(self, call):
        i = min(call["reply_i"], len(self.replies) - 1)
        call["reply_i"] += 1
        call["transcript"].append({"speaker": "callee",
                                   "text": self.replies[i]})

    def __call__(self, method, url, json=None, params=None, headers=None,
                 timeout=None):
        path = url.split("://", 1)[-1].split("/", 1)[-1]
        self.requests.append((method, "/" + path, json))
        body = self._route(method, "/" + path, json or {}, params or {})

        class _Resp:
            def raise_for_status(self):
                pass

            def json(self):
                return body
        return _Resp()

    def _route(self, method, path, body, params):
        if path == "/external/call":
            assert body.get("greeting"), "greeting is mandatory"
            self._n += 1
            cid = f"r{self._n}"
            call = {"transcript": [{"speaker": "assistant",
                                    "text": body["greeting"]}],
                    "reply_i": 0, "status": "active",
                    "number": body["number"]}
            self.calls[cid] = call
            self._reply(call)          # the callee answers the greeting
            return {"call_id": cid, "status": "calling", "transport": "gsm"}
        cid, action = path.split("/")[2:4]
        call = self.calls[cid]
        if action == "say":
            call["transcript"].append({"speaker": "assistant",
                                       "text": body["text"]})
            self._reply(call)
            return {"status": "queued", "call_id": cid}
        if action == "heard":
            after = int(params.get("after", -1))
            for i in range(after + 1, len(call["transcript"])):
                if call["transcript"][i]["speaker"] != "assistant":
                    return {"text": call["transcript"][i]["text"], "index": i,
                            "status": call["status"]}
            return {"text": None, "index": len(call["transcript"]) - 1,
                    "status": call["status"]}
        if action == "transcript":
            return {"transcript": list(call["transcript"])}
        if action == "hangup":
            call["status"] = "ended"
            return {"call_id": cid, "status": "ended", "transport": "gsm",
                    "duration_s": 12.5,
                    "transcript": list(call["transcript"])}
        raise AssertionError(f"unexpected {method} {path}")


def make(bridge=None):
    return CallAPICallAdapter(base_url="http://bridge:8770", token="t",
                              http_request=bridge or FakeBridge())


def test_first_speak_becomes_the_greeting():
    bridge = FakeBridge()
    adapter = make(bridge)
    cid = adapter.initiate_call("+390000000000", "confirm appointment")
    assert not bridge.requests               # nothing on the wire yet
    adapter.speak(cid, "This is an automated AI assistant calling.")
    method, path, body = bridge.requests[0]
    assert (method, path) == ("POST", "/external/call")
    assert body["greeting"] == "This is an automated AI assistant calling."
    first = bridge.calls["r1"]["transcript"][0]
    assert first == {"speaker": "assistant",
                     "text": "This is an automated AI assistant calling."}


def test_listen_advances_and_never_replays():
    adapter = make(FakeBridge(replies=["uno", "due"]))
    cid = adapter.initiate_call("+390000000000", "x")
    adapter.speak(cid, "disclosure")
    assert adapter.listen(cid)["text"] == "uno"
    adapter.speak(cid, "seconda battuta")
    assert adapter.listen(cid)["text"] == "due"
    assert adapter.listen(cid, timeout_s=0.1)["text"] == ""


def test_terminate_builds_call_result():
    adapter = make()
    cid = adapter.initiate_call("+390000000000", "confirm")
    adapter.speak(cid, "disclosure")
    result = adapter.terminate_call(cid)
    assert result.status == "completed"
    assert result.duration_s == 12.5
    assert result.metadata["transport"] == "gsm"
    assert result.transcript[0]["speaker"] == "assistant"


def test_never_placed_call_terminates_as_failed():
    adapter = make()
    cid = adapter.initiate_call("+390000000000", "x")
    result = adapter.terminate_call(cid)
    assert result.status == "failed"


def test_port_conformance_against_fake_bridge():
    assert voice_port.conformance(make()) == []


def test_wrapper_keeps_disclosure_first_over_the_wire():
    """voice.call (compliance wrapper) + adapter + fake bridge end-to-end:
    the AI disclosure must be the first line CallAPICall pronounces."""
    bridge = FakeBridge(replies=["ok"])
    reg = ToolRegistry()
    register_external_ports(reg, voice=make(bridge), principal="Andrea")
    r = reg.execute("voice.call", {"number": "+390000000000",
                                   "purpose": "demo",
                                   "lines": ["Confermo per domani."]})
    assert r.status == "ok"
    assert r.observation["trust"] == "untrusted"
    spoken = [e["text"] for e in bridge.calls["r1"]["transcript"]
              if e["speaker"] == "assistant"]
    assert "AI assistant" in spoken[0] and "Andrea" in spoken[0]
    assert spoken[1] == "Confermo per domani."


@pytest.mark.skipif(os.environ.get("CALLBRIDGE_LIVE") != "1",
                    reason="live bridge check is opt-in (CALLBRIDGE_LIVE=1); "
                           "it only pings /health, never dials")
def test_live_bridge_health():
    import requests
    url = os.environ.get("CALLBRIDGE_CONTROL_URL", "http://127.0.0.1:8770")
    r = requests.get(url.rstrip("/") + "/health", timeout=5)
    assert r.status_code == 200 and r.json().get("status") == "ok"
