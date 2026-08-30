# Phase 1 — Persistent operation, capabilities, dynamic reprioritization

The second vertical slice. The loop from Phase 0 now survives restarts,
imports external capabilities under security gates, carries a reference
production adapter behind the LLM port, and demonstrates the canonical
"goals are dynamic" behavior from the design documents.

## 1. Recovery and persistent operation

`Controller.recover()` restores everything that is not a projection
from the event log: the cycle counter, the deterministic id counters
(no id collisions across restarts), the pending human decision (the
decision inbox survives a crash), denied-proposal signatures, emitted
conflicts, the logical clock offset, and the control state — a system
stopped with STOP **stays stopped** across restarts until an explicit
human RESUME. `scenario.toy.create(db_path=...)` on an existing store
skips world building and recovers instead; the server gains true
persistence with `--db pgdca.db`.

## 2. Imported skills and MCP servers (requirement M28)

- **Skill packages** (`pgdca/tools/skills.py`): a directory with
  `skill.json` (name, description, version, risk_class, triggers) and
  `SKILL.md`. Imported skills carry `provenance=imported`,
  `trust=untrusted`; their text is data, never instructions. Progressive
  disclosure: only skills whose triggers match the current context enter
  the LLM briefing. A risky skill imported by the system stays
  PENDING_HUMAN; enabling at EXTERNAL_COMMUNICATION or above is
  human-only.
- **MCP servers** (`pgdca/tools/mcp_client.py`, dependency-free stdio
  JSON-RPC client): on import the registry connects, enumerates tools
  and registers each as `<server>.<tool>` at the restrictive default
  risk class EXTERNAL_COMMUNICATION with untrusted descriptions
  (description poisoning defense). System imports stay disabled until
  human approval; execution of a disabled tool is refused at the
  registry. Connections are lazy and re-established after recovery.
  Subprocess isolation is the Phase 1 sandbox boundary.
- Samples: `examples/skills/procurement-discipline/`,
  `examples/mcp/toy_market_server.py`. Both import from the GUI
  (Capabilities tab) or via `/api/skills/import` and `/api/mcp/import`.

## 3. Anthropic reference adapter

`pgdca/cognition/anthropic_adapter.py` — one adapter behind `LlmPort`
(the owner's provider library plugs in the same way). Defaults:
`claude-opus-5`, server-side refusal fallbacks enabled
(`betas=["server-side-fallback-2026-07-01"]`, `fallbacks="default"`),
refusals raise into the gateway's repair/escalation path, instructions
live in the system prompt while the request context travels as data
with the injection doctrine restated. Optional dependency:
`pip install -e ".[anthropic]"`; run with
`python -m pgdca.api.server --adapter anthropic`.

## 4. Dynamic reprioritization

A generic reconciliation rule: a target whose every acquisition route
(factor and substitutes) has a *known* cost above the remaining budget
is **DEFERRED** — revisitable, not abandoned — with `TARGET_DEFERRED`
and `RESOURCE_REALLOCATED` events. Unknown costs never trigger
deferral (possibility is preserved until verified).

`pgdca/scenario/opportunity.py` replays the documents' example: mid-
preparation, investor meetings appear (ENVIRONMENT-provenance events,
`OPPORTUNITY_DETECTED`); arbitration prefers the meeting (two distinct
goal paths beat the boots' summit+trip paths), the human approves the
big ticket, the starved trip targets defer, the affordable snack
substitution still completes — and the persistent goals themselves
never change without the human.

## Verification

51 tests green (`pytest`): the 35 from Phase 0 plus recovery (pending
decision and STOP across restarts, id-collision freedom, denied
signatures), capabilities (validation, disclosure, human gates, MCP
roundtrip and post-recovery reconnection), the adapter (defaults,
fallbacks, refusal path, fenced JSON, conformance) and the
reprioritization acceptance (plus a no-spurious-deferrals guard on the
base scenario). GUI exercised live via Playwright: skill and MCP
server imported from the browser forms.

## Next slices

- richer strategy branching (multi-step strategies with the
  PROPOSED→TESTING→ACTIVE→PRUNED lifecycle);
- browser/email/voice ports (interface-first, per spec Phase 5);
- WebSocket push + multi-user identity for the GUI;
- hardened sandbox for imported tools; compensation machinery for
  revoked-but-executed actions.
