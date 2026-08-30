# Phase 9 — Exogenous inputs, extended interaction, settings GUI (M31–M33)

Rev. 5 user requirements: human decisions and world facts entering the
*running* process as first-class graph citizens, richer bidirectional
interaction, and structured settings for the Phase 8 features — all
shaped for the future instance network (`docs/future_features.md`).

## M31 — Directives and Facts (`pgdca/exogenous.py`)

Two new node kinds in the causal graph:

- **DIRECTIVE** — a normative human decision issued mid-flight: a new
  short/long-horizon target, an imposed limit or thing to avoid, a
  context change. Weight = `priority`. **DIRECTIVE is in `GOAL_KINDS`**,
  so an ACTIVE directive is a propagation anchor: `goal_effects`, U(a),
  antagonisms and critique weigh it automatically among all existing
  decision points — no special-casing anywhere.
- **FACT** — a descriptive scenario change, `imposed` (true on arrival:
  a law, an inheritance) or an `opportunity` the human accepts or
  declines. Weight = `importance`; it acts through its typed edges.

**Integration = consensus before weaving** (the vacation flow). The
gateway role `integrate` proposes typed weighted edges against the
existing graph ("avoid meetings" → BLOCK edges), new plan subtargets,
deferrals, budget impacts and detected conflicts; the proposal opens a
system deliberation thread (optionally after cross-AI review — the new
`integration` checkpoint in the M29 matrix). Resolving it
confirmed/modified weaves everything with human provenance: edges
VALIDATED (`integration_agreed:<id>`), spawned targets created (the
explicit human confirmation ratifies them — M1 intact), deferrals
applied. Budget impacts are **never** automatic (M3 ratchet): they are
listed for the human to apply as change-set ops in the same
resolution. Below `exogenous_auto_weave_below` weight, edges self-apply
as HYPOTHESIZED under the existing graph guardrails; opportunities and
non-owner inputs never auto-weave.

**CRUD with re-evaluation.** Updates emit `HUMAN_EDIT` +
`REEVALUATION_REQUESTED` and dirty the subgraph (the event-driven
reconciler re-scores it); **Re-integrate** re-runs the weaving analysis
in a fresh thread. Deletion is event-sourced retirement: every touching
edge is invalidated, integration-spawned nodes go to an
**orphan-review thread**, and blocked targets reactivate.

**Deterministic blocking, reversible.** A TARGET with an active
BLOCK/INHIBIT edge from an ACTIVE directive/fact is deferred by the
reconciler (`deferred_by` marker) and **reactivates the moment the
blocker is retired** — "no meetings while the vacation stands", undone
by ending the vacation.

**Federation-ready.** Every node carries an `origin` envelope
`{source, authority, instance}`. The trust rule is live today: any
authority other than `owner` is external content — CONTENT_INGESTED
(taint), ground-checkable, consensus always required, never
auto-active. Future superior/peer instances enter through this same
channel (see `future_features.md`).

## M32 — Extended interaction

- **Typed change-set ops** in any thread resolution: `node_props`,
  `new_directive`, `new_fact`, `propose_goal` (+ ratify),
  `defer_target`, `set_budget`, `create_guardrail` — each routed
  through its existing human-identity channel. Any conversation can,
  on the human's request, modify the overall scenario and targets.
- **Scenario threads**: subject kind `scenario` with a whole-picture
  evidence packet (goals, open/deferred targets, budget, active
  directives/facts) — "Discuss the overall scenario" in the GUI; the
  mock proposes budget ops from the question.
- **AI-initiated consultations**: a conflict touching a human directive
  opens a consultation thread ("how should I weigh this?"); a periodic
  sync thread is available config-gated
  (`consultation_interval_cycles`, default off). Together with the
  existing escalation, review-disagreement and integration threads, the
  AI can request discussion wherever it needs the human's judgment.

## M33 — Settings GUI

Structured panels at the top of the Config tab, writing through the
existing config/guardrail APIs: the **cross-AI review matrix** (per
checkpoint: enabled, max rounds, disagreement override, min risk),
**grounding** (list/toggle ground-check guardrails, one-click creation,
knowledge count), and **exogenous & consultations** (consensus toggle,
auto-weave threshold, consultation cadence). The raw config table
remains below as the power fallback.

## Verification

134 tests green: the 121 from Phase 8 plus 13 exogenous tests (CRUD +
events + origin envelope + human-only edits; the vacation directive
weaving on consensus with SUPPORT/BLOCK edges, plan subtarget and
deferral; the woven directive weighing in `goal_effects`/U(a);
reversible blocking through retire; orphan review on retirement;
imposed vs opportunity facts with accept/decline; auto-weave below
threshold as HYPOTHESIZED; non-owner origins forced external and never
auto-active; the integration review checkpoint; scenario threads with
4-op change-sets incl. ratify-in-one-act; conflict-with-directive and
periodic consultations; recovery of nodes, threads and id counters).
Deterministic replay and the bench hold (baseline regenerated: token
counts shift ~0.5% for the new context fields; every property metric
unchanged). World inputs tab and settings panels verified live via
Playwright.
