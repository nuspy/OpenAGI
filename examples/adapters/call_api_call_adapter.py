"""CallAPICall adapter behind VoiceCallPort (local integration).

CallAPICall (C:/Projects/callAPIcall) is the owner's voice/phone suite:
real cellular calls over a GSM USB modem or an Android phone, with local
STT/TTS. Its control server (Flask, :8770) exposes the externally-driven
call API this adapter maps the port onto (call-bridge/callbridge/
api_external.py):

    POST /external/call                {number, greeting, voice?, lang?}
    POST /external/<id>/say            {text}
    GET  /external/<id>/heard          ?after=N&timeout_s=T
    GET  /external/<id>/transcript
    POST /external/<id>/hangup

Design points:

- the tool wrapper (pgdca/tools/external.py) speaks the AI disclosure as
  the FIRST line of every call; this adapter defers the actual
  `POST /external/call` until that first `speak()`, whose text becomes
  the call `greeting` - CallAPICall pronounces the greeting before
  anything else, so the disclosure-first guarantee survives the wire;
- transcripts come back as data; the trust labeling stays in the
  wrapper (untrusted), as everywhere else;
- the port conformance suite dials a REAL number: run it only manually,
  against a test number the owner supplies (docs/LOCAL_INTEGRATIONS.md).

Configuration (env vars; the token lives in CallAPICall's local
config.json, never in this repo):

    CALLBRIDGE_CONTROL_URL     default http://127.0.0.1:8770
    CALLBRIDGE_CONTROL_TOKEN   Bearer token of the control server
    CALLBRIDGE_VOICE / CALLBRIDGE_LANG   optional TTS voice/language
"""
from __future__ import annotations

import os

from pgdca.ports.voice import CallResult


class CallAPICallAdapter:
    def __init__(self, base_url: str | None = None, token: str | None = None,
                 voice: str | None = None, lang: str | None = None,
                 http_request=None, call_timeout_s: float = 75.0):
        self.base_url = (base_url or os.environ.get(
            "CALLBRIDGE_CONTROL_URL", "http://127.0.0.1:8770")).rstrip("/")
        self.token = token if token is not None else os.environ.get(
            "CALLBRIDGE_CONTROL_TOKEN", "")
        self.voice = voice or os.environ.get("CALLBRIDGE_VOICE") or None
        self.lang = lang or os.environ.get("CALLBRIDGE_LANG") or None
        self.call_timeout_s = call_timeout_s
        if http_request is None:
            import requests  # deferred: only needed for the real bridge
            http_request = requests.request
        self._request = http_request
        self._calls: dict[str, dict] = {}
        self._n = 0

    # ----------------------------------------------------------- plumbing

    def _http(self, method: str, path: str, body: dict | None = None,
              params: dict | None = None, timeout: float | None = None) -> dict:
        headers = {}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        resp = self._request(method, self.base_url + path, json=body,
                             params=params, headers=headers,
                             timeout=timeout or self.call_timeout_s)
        resp.raise_for_status()
        return resp.json()

    def _call(self, call_id: str) -> dict:
        try:
            return self._calls[call_id]
        except KeyError:
            raise KeyError(f"unknown call: {call_id}") from None

    # --------------------------------------------------- VoiceCallPort

    def initiate_call(self, number: str, purpose: str) -> str:
        """Registers the intent; the wire call starts at the first speak().

        The wrapper's first spoken line is the AI disclosure: making it the
        CallAPICall `greeting` guarantees it is pronounced before anything
        else on the real call."""
        self._n += 1
        cid = f"capc_{self._n}"
        self._calls[cid] = {"number": number, "purpose": purpose,
                            "remote": None, "last_index": -1}
        return cid

    def answer_call(self) -> str | None:
        # incoming calls stay with CallAPICall's own agent for now
        return None

    def speak(self, call_id: str, text: str) -> None:
        c = self._call(call_id)
        if c["remote"] is None:
            body = {"number": c["number"], "greeting": text}
            if self.voice:
                body["voice"] = self.voice
            if self.lang:
                body["lang"] = self.lang
            out = self._http("POST", "/external/call", body)
            c["remote"] = out["call_id"]
            c["transport"] = out.get("transport")
            return
        self._http("POST", f"/external/{c['remote']}/say", {"text": text})

    def listen(self, call_id: str, timeout_s: float = 15.0) -> dict:
        c = self._call(call_id)
        if c["remote"] is None:
            return {"text": "", "speaker_state": "unknown"}
        out = self._http("GET", f"/external/{c['remote']}/heard",
                         params={"after": c["last_index"],
                                 "timeout_s": timeout_s},
                         timeout=timeout_s + 15.0)
        c["last_index"] = int(out.get("index", c["last_index"]))
        return {"text": out.get("text") or "",
                "speaker_state": "unknown"}   # no affect signal upstream

    def transcribe(self, call_id: str) -> list:
        c = self._call(call_id)
        if c["remote"] is None:
            return []
        out = self._http("GET", f"/external/{c['remote']}/transcript")
        return list(out.get("transcript", []))

    def detect_speaker_state(self, call_id: str) -> str:
        return "unknown"   # CallAPICall does not expose an affect signal

    def terminate_call(self, call_id: str) -> CallResult:
        c = self._call(call_id)
        if c["remote"] is None:
            # never went on the wire (nothing was ever spoken)
            return CallResult(call_id=call_id, status="failed",
                              metadata={"number": c["number"],
                                        "reason": "call never placed"})
        out = self._http("POST", f"/external/{c['remote']}/hangup")
        transcript = list(out.get("transcript", []))
        heard = any(e.get("speaker") != "assistant" for e in transcript)
        return CallResult(
            call_id=call_id,
            status="completed" if heard else "no_answer",
            transcript=transcript,
            duration_s=float(out.get("duration_s", 0.0)),
            metadata={"number": c["number"], "purpose": c["purpose"],
                      "transport": out.get("transport"),
                      "remote_call_id": c["remote"]})
