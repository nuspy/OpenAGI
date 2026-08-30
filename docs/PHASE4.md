# Phase 4 — Deliberation: in-progress human-AI co-decision (M27)

The user requirement behind this slice: *"GUI per comunicazione in
itinere uomo-AI per ridiscutere decisioni e strategie (con componente
associato)"* — a component, not just a view. `pgdca/collaboration/
deliberation.py` ships it, plus live events for the console (M25's
SSE requirement).

## 1. Discussion threads on anything

The human opens a thread on any **decision, graph node, strategy
branch, guardrail or contradiction** ("Discuss" buttons across the
GUI; `POST /api/deliberations`). Threads and every message in them are
events (`DELIBERATION_OPENED/MESSAGE/RESOLVED`) over a projection —
recovery-safe and replay-safe like everything else.

## 2. Evidence-grounded answers

The system's replies are built in two layers, keeping the authority
split intact:

- a **deterministic evidence packet** reconstructed from projections —
  the journal rationale (verdict, alternatives with utilities,
  counterfactual, execution) for decisions, node state + goal effects +
  decision history for nodes, branch state for strategies, the claim
  pair for contradictions;
- the **gateway role `deliberate`** words the answer from that packet
  (instructions and data stay separated; the mock is deterministic).
  A numeric proposal in the question ("set importance to 0.4") comes
  back as a **structured suggestion**, never a silent edit.

## 3. Binding outcomes, human-only

Only the human resolves a thread; the outcome is an event with recorded
effects that run through the existing channels:

- **confirmed** — agreement recorded;
- **modified** — the agreed node edits are applied as `HUMAN_EDIT`
  (human provenance, same path as manual GUI edits); one click applies
  a system suggestion;
- **cancelled** — a *pending* decision is denied; an *executed* one is
  revoked through the supervisor override, triggering the Phase 3
  compensation path (refund, budget restored); an *active strategy* is
  deferred (`STRATEGY_CHANGED`, honest replan next cycle).

## 4. Escalation as a thread (bidirectional)

Both escalation paths (`no viable hypotheses`, `unstable with no
information-gain action`) now open a **system-authored thread** carrying
the escalation packet (reason, cycle, remaining budget, open targets).
The human answers in place and closes it. This path emits no LLM calls,
so deterministic replay stays LLM-free on escalations.

## 5. Dissent feeds the self-model

Resolving a decision thread as *cancelled* or *modified* stamps a
**dissent mark** on that decision's context signature (the same
abstraction the audit and policy engine use). Future decisions with the
same signature carry an `[advisory] the human contested N similar
decision(s) in deliberation` reason on their supervisor verdict — the
discussions literally feed future oversight, as the spec requires
("le discussioni alimentano audit e policy learning").

## 6. Live console (SSE)

The GUI now listens to `/api/events/stream` (Server-Sent Events): new
events stream into the Events tab and trigger a debounced refresh, with
the old polling kept as a 5-second safety net. The `Deliberation` tab
badge counts open threads like the inbox badge counts pending
decisions.

## Verification

82 tests green: the 72 from Phase 3 plus 10 deliberation tests
(evidence-grounded answers and replies, human-only open/reply/resolve
with a 409 on double resolution, unknown subjects, modified→HUMAN_EDIT,
cancel-pending→denied, cancel-executed→compensated refund,
cancel-strategy→deferred + successful replan, escalation auto-thread
answered and closed, dissent advisory surfacing on a later boots
verdict, threads + id counters surviving restart recovery). The
deterministic-replay acceptance test still passes. Deliberation tab
verified live via Playwright (open decision thread with system answers,
node thread resolved as modified).
