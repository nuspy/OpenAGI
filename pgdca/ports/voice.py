"""Voice call port - the Call Happy Call integration point (spec §20).

The cognitive architecture sees only this generic interface; the
existing local application connects later as an adapter (bridge where
APIs differ). Transcripts are untrusted data. The tool wrapper (not
the adapter) enforces the AI disclosure as the first spoken line.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass
class CallResult:
    call_id: str
    status: str                     # completed | failed | no_answer
    transcript: list = field(default_factory=list)   # [{"speaker","text"}]
    duration_s: float = 0.0
    metadata: dict = field(default_factory=dict)


class VoiceCallPort(Protocol):
    def initiate_call(self, number: str, purpose: str) -> str: ...
    def answer_call(self) -> str | None: ...
    def speak(self, call_id: str, text: str) -> None: ...
    def listen(self, call_id: str, timeout_s: float = 15.0) -> dict: ...
    def transcribe(self, call_id: str) -> list: ...
    def detect_speaker_state(self, call_id: str) -> str: ...
    def terminate_call(self, call_id: str) -> CallResult: ...


class MockVoiceAdapter:
    """Deterministic scripted counterpart for tests and dry runs."""

    def __init__(self, replies: list[str] | None = None):
        self.replies = list(replies or ["Understood, thank you."])
        self.calls: dict[str, dict] = {}
        self._n = 0

    def initiate_call(self, number: str, purpose: str) -> str:
        self._n += 1
        cid = f"call_{self._n}"
        self.calls[cid] = {"number": number, "purpose": purpose,
                           "spoken": [], "transcript": [], "reply_i": 0}
        return cid

    def answer_call(self) -> str | None:
        return None

    def speak(self, call_id: str, text: str) -> None:
        c = self.calls[call_id]
        c["spoken"].append(text)
        c["transcript"].append({"speaker": "assistant", "text": text})

    def listen(self, call_id: str, timeout_s: float = 15.0) -> dict:
        c = self.calls[call_id]
        reply = self.replies[min(c["reply_i"], len(self.replies) - 1)]
        c["reply_i"] += 1
        c["transcript"].append({"speaker": "callee", "text": reply})
        return {"text": reply, "speaker_state": "calm"}

    def transcribe(self, call_id: str) -> list:
        return list(self.calls[call_id]["transcript"])

    def detect_speaker_state(self, call_id: str) -> str:
        return "calm"

    def terminate_call(self, call_id: str) -> CallResult:
        c = self.calls[call_id]
        return CallResult(call_id=call_id, status="completed",
                          transcript=list(c["transcript"]),
                          duration_s=float(len(c["transcript"]) * 5),
                          metadata={"number": c["number"]})


def conformance(port: VoiceCallPort) -> list[str]:
    problems: list[str] = []
    try:
        cid = port.initiate_call("+000000000", "conformance probe")
        port.speak(cid, "probe")
        heard = port.listen(cid, timeout_s=1.0)
        if not isinstance(heard, dict) or "text" not in heard:
            problems.append("listen must return a dict with 'text'")
        if not isinstance(port.transcribe(cid), list):
            problems.append("transcribe must return a list")
        result = port.terminate_call(cid)
        if not isinstance(result, CallResult):
            problems.append("terminate_call must return a CallResult")
    except Exception as exc:  # noqa: BLE001
        problems.append(f"lifecycle raised: {exc!r}")
    return problems
