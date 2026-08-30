"""Skeleton: connect the existing CallAPICall project as the voice
adapter (local development - the project lives on your machine).

Fill the TODOs, then:

    from pgdca.ports.voice import conformance
    assert conformance(CallAPICallAdapter()) == []

    from pgdca.tools.external import register_external_ports
    register_external_ports(ctrl.registry, voice=CallAPICallAdapter(),
                            principal="<your name>")

Notes:
- `voice.call` (the tool wrapper) speaks the AI disclosure as the first
  line - the adapter must not strip it;
- transcripts you return are treated as untrusted data by the
  architecture; recording/consent handling per jurisdiction belongs in
  the CallAPICall side or here, before returning results.
"""
from __future__ import annotations

from pgdca.ports.voice import CallResult


class CallAPICallAdapter:
    def __init__(self):
        # TODO(local): import the CallAPICall client/API here.
        raise NotImplementedError("wire the local CallAPICall project here")

    def initiate_call(self, number: str, purpose: str) -> str:
        raise NotImplementedError  # TODO(local): CHC initiate_call()

    def answer_call(self) -> str | None:
        raise NotImplementedError  # TODO(local): CHC answer_call()

    def speak(self, call_id: str, text: str) -> None:
        raise NotImplementedError  # TODO(local): CHC speak()/TTS

    def listen(self, call_id: str, timeout_s: float = 15.0) -> dict:
        raise NotImplementedError  # TODO(local): CHC listen()/STT
        # return {"text": ..., "speaker_state": ...}

    def transcribe(self, call_id: str) -> list:
        raise NotImplementedError  # TODO(local): structured transcript events

    def detect_speaker_state(self, call_id: str) -> str:
        raise NotImplementedError  # TODO(local): CHC detect_speaker_state()

    def terminate_call(self, call_id: str) -> CallResult:
        raise NotImplementedError  # TODO(local): close + build CallResult
