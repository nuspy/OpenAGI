# Phase 0 — Minimum Viable Loop: implementation notes

Phase 0 implements the complete cognitive loop end-to-end on a toy
domain, exactly as prescribed by the implementation specification
(v1.1, *Implementation Phases → Phase 0*): single process, single
relational store, API-first backend with a minimal GUI, minimal Tier 1
guardrails and Decision Supervisor. **The loop closes; every later
phase grows a working system.**

## What runs

```
goal → reconciliation → context → hypotheses (LLM port) → critique
     → arbitration U(a) + sensitivity gate → DECISION_MADE
     → Decision Supervisor verdict → execute (tools) → observe
     → verify → journal → audit (dq ≠ oq) → policy learning
     → calibration → loop
```

Toy domain: the mountain-trip scenario from the design documents — two
persistent goals (summit vs diet), a EUR 500 budget, factors with
different importance/substitutability (boots 400, helmet 80, energy
bars 10×20, dried fruit 10×2), a scripted stock-out failure, and an
adversarial advert carrying a price-manipulation injection.

## How to run

```bash
pip install -e ".[api,dev]"        # or: pip install fastapi uvicorn pytest httpx

pytest                             # 35 tests, including the acceptance scenario
python -m pgdca.scenario.toy       # scripted CLI demo (auto-driven human)
python -m pgdca.api.server         # backend + GUI at http://127.0.0.1:8000
```

In the GUI: **Step** advances one cycle; the **Decision inbox** holds
HUMAN_REQUIRED verdicts (approve/deny, override in either direction);
**Inject advert** demonstrates the injection defense live; every node in
the **Graph** opens a detail dialog with editable weights and a
"Discuss" deliberation view reconstructed from the journal.

## Traceability: implementation → specification (v1.1)

| Module | Spec sections | Non-negotiables |
|---|---|---|
| `pgdca/store.py`, `runtime.py` | Event Sourcing, Consistency and Deterministic Replay (§28) | #32 |
| `pgdca/domain.py`, `graph.py` | Global Cognitive Graph (§7), Relationship Model (§8), Causal Propagation + guardrails (§10), Appendix A | #4, #5, #6, #7 |
| `pgdca/arbitration.py` | Goal Arbitration (§5), Marginal Value (§6), canonical U(a) (Appendix A.3), sensitivity gate (§5) | #8 |
| `pgdca/security/guardrails.py` | Two-Tier Guardrail System (§71) | #30 |
| `pgdca/security/supervisor.py` | Decision Supervisor (§72), Tool Execution Contract risk classes (§53) | #31 |
| `pgdca/security/budgets.py` | Human Authorization and Bounded Autonomy (§54) | #29 |
| `pgdca/security/taint.py` | Prompt Injection Defense (§73) | #28 |
| `pgdca/cognition/gateway.py` | LLM Interface (§52), Ports & Adapters (§16) | #33 |
| `pgdca/cognition/mock_llm.py` | mock adapter behind the `llm_provider` port (the user's provider library plugs in later as an adapter) | #33 |
| `pgdca/memory/journal.py` | Persistent Audit Journal (§27) | #24 |
| `pgdca/memory/audit.py` | Decision vs Outcome Quality (§30), Audit Engine (§29), Failure Handling (§66) | #12 |
| `pgdca/memory/policies.py` | Decision Abstraction (§31), Policy Representation + SHADOW lifecycle (§32) | #13, #14 |
| `pgdca/memory/calibration.py` | Prediction and Calibration (§47), Cold Start / apprentice mode (§48) | — |
| `pgdca/controller.py` | Controller Responsibilities (§51), State Machine (§60), Reconciliation (§49, incremental), Goal Integrity (§69), corrigibility | #25, #26, #27 |
| `pgdca/tools/registry.py` | Tool Graph (§15), acquisition security (§14) | #33 |
| `pgdca/api/server.py`, `pgdca/ui/index.html` | GUI and API Layer (§62), In-Progress Co-Decision (§78) | — |
| `pgdca/scenario/toy.py` | Phase 0 acceptance scenario (§75) | — |

Section numbers refer to the v1.1 specification.

## Acceptance criteria (all verified by `tests/`)

- the loop closes on the toy domain and reaches IDLE with all targets
  satisfied (`test_acceptance.py::test_full_scenario_with_injection`);
- the hard budget is respected to the cent; over-budget actions are
  DENIED with `BUDGET_EXHAUSTED` (`test_security.py`);
- Tier 1 guardrails are technically non-writable by the system
  identity, at the store and over the API (`test_security.py`,
  `test_api.py`); Tier 2 activation is asymmetric (restrictive
  self-activates, permissive waits for the human);
- every executed action carries a prior supervisor verdict; the human
  can override in both directions and overrides are audited;
- PAUSE/STOP are honored unconditionally between cycle steps — a STOP
  issued mid-cycle prevents execution (`test_controller.py`);
- meta/persistent goals activate only through human ratification;
- external content is data: the injected "special offer" is proposed by
  the (deliberately naive) mock LLM, tainted, escalated with
  `INJECTION_SUSPECTED`, denied, and never executed; the real purchase
  later happens at the market price;
- decision quality ≠ outcome quality: the scripted stock-out yields
  dq=1.0 / oq=0.1 with `environmental_uncertainty` classified;
- recurring well-made decisions become a policy through the abstraction
  role, entering SHADOW mode and activating only after logged
  agreements; the seed policy ships ACTIVE with `seed` provenance;
- cross-goal antagonism (bars harm the diet) lowers arbitration utility
  and is recorded as `CONFLICT_DETECTED`; opportunity cost prioritizes
  the critical non-substitutable enabler; the sensitivity gate flags
  unstable rankings and prefers information gain;
- deterministic replay: re-running the scenario against the recorded
  LLM I/O reproduces the decision trace **byte-identically**, timestamps
  included (`test_acceptance.py::test_deterministic_replay_reproduces_decisions`).

## Deliberate Phase 0 limits (next slices)

- The LLM port has mock + replay adapters only; the production adapter
  (the owner's provider library) plugs in behind `LlmPort`.
- Voice, email/SMS, browser, vault: ports reserved, not yet defined
  (Phase 5 of the spec); skills/MCP import is Phase-planned (spec §82).
- The GUI covers graph/inbox/guardrails/journal/policies/events; the
  full configuration surface and WebSocket push are next.
- X-Actor header is a Phase 0 identity stub; real authentication
  arrives with the multi-user GUI slice.
- Compensation for revoked-but-executed actions is recorded, not yet
  enacted (rollback machinery is a later slice).
