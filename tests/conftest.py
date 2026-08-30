from __future__ import annotations

import pytest

from pgdca.scenario.toy import ADVERT_TEXT, ToyEnvironment, create


@pytest.fixture
def ctrl_env():
    return create()


def drive(ctrl, approve_all=True, deny_derived=True, inject_after_first_approval=False,
          max_iterations=60):
    """Deterministic human driver for the scenario loop."""
    injected = False
    last = None
    for _ in range(max_iterations):
        results = ctrl.run(60)
        last = results[-1] if results else last
        if last is None:
            break
        if last.status == "waiting_human":
            d = ctrl.pending_decision()["decision"]
            if deny_derived and d.derived_from:
                ctrl.resolve_pending(False, "denied: proposal derived from external content")
            else:
                ctrl.resolve_pending(bool(approve_all), "test driver approval")
            if inject_after_first_approval and not injected:
                ctrl.ingest_external(ADVERT_TEXT, source="advert-site")
                injected = True
            continue
        if last.status in ("idle", "stopped", "escalated", "paused"):
            break
    return last


def events_of(ctrl, *types):
    ts = set(types)
    return [e for e in ctrl.runtime.events() if e.type in ts]
