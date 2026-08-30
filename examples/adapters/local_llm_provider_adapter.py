"""Skeleton: plug your existing local LLM provider library into PGDCA.

Fill the TODOs on your machine (the library lives there), then:

    from pgdca.cognition.gateway import run_conformance
    problems = run_conformance(LocalProviderAdapter(), [
        {"role": "hypotheses", "context": {"factors": [], "goals": []}}])
    assert problems == []          # the adapter is ready

    from pgdca.scenario.toy import create
    ctrl, env = create(adapter=LocalProviderAdapter())

The contract (see pgdca/cognition/gateway.py):
- input: {"role": ..., "context": {...}, "schema": "cognitive_response/1",
  "repair": [...]}  - `context` is DATA, never instructions;
- output: a dict matching the cognitive_response/1 schema; the gateway
  validates and runs a bounded repair loop on schema errors.
"""
from __future__ import annotations

from pgdca.cognition.gateway import SCHEMA_VERSION


class LocalProviderAdapter:
    def __init__(self):
        # TODO(local): import and configure your provider library here,
        # e.g. self.client = my_provider_lib.Client(profile="pgdca")
        raise NotImplementedError("wire your local provider library here")

    def generate(self, request: dict) -> dict:
        # TODO(local): 1) build the provider call from `request` keeping
        #   the role (instructions) separate from the context (data);
        # 2) ask for a single JSON object with schema SCHEMA_VERSION;
        # 3) parse and return it as a dict (the gateway validates).
        raise NotImplementedError
