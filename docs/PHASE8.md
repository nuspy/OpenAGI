# Phase 8 — Cross-AI review (M29) + RAG ground-check (M30)

Two user requirements from rev. 4 of the review: a second AI that
reviews the primary's sensitive outputs before they are enacted, and an
anti-hallucination grounding check inside the existing guardrail
system. Both are **optional** and off by default; enabling them changes
no other behavior (the whole prior suite passes untouched).

## M29 — Cross-AI review (`pgdca/cognition/reviewer.py`)

**The reviewer is a port.** Any `LlmPort` adapter can be the second AI
(a different provider/model in local deployment — the user's own
library, or `AnthropicLlmAdapter` with another model). It runs behind
its own `LlmGateway`, so every exchange is an `LLM_REQUEST/RESPONSE/
USAGE` event: logged, replayable, cost-accounted per role (`review`,
`defend`, `decide` appear in the Learning tab's usage table). The
bundled `MockReviewerAdapter` is deterministic.

**Optional and granular.** `Config.review_matrix` — runtime-editable
like every Config field (Config tab, `POST /api/config`) — holds one
policy per checkpoint:

```json
{"decision":      {"enabled": true, "max_rounds": 2,
                   "on_disagreement": "human", "min_risk_class": "FINANCIAL"},
 "strategy":      {"enabled": false, "max_rounds": 2, "on_disagreement": "human"},
 "retrospective": {"enabled": false, "max_rounds": 1,
                   "on_disagreement": "primary_decides"}}
```

Checkpoints cover the sensitive points the user named: **decision**
(every significant decision, i.e. the enactment of actions — gated at
or above `min_risk_class`), **strategy** (the setting and management of
subtargets: strategy branches), **retrospective** (the regressive
analyses: audit + counterfactual).

**Consensus protocol** (mechanics deterministic, wording generative).
Each interaction: the reviewer's `review` role returns objections
(empty = agree); the primary's `defend` role returns maintained points
with evidence (empty = the primary **concedes**, and the subject is
**withdrawn** — a conceded decision is pruned and never enacted).
Outcomes:

- `consensus` — proceed; agreed points accumulate per checkpoint;
- `withdrawn` — not enacted;
- rounds exhausted → the matrix override decides:
  - `"human"` → **the final decision is discussed with the human before
    being enacted**: a decision's verdict is forced to HUMAN_REQUIRED
    with the standing objections as `[review]` reasons; a strategy
    branch is deferred, a system deliberation thread opens, and
    replanning pauses until the human resolves it; a contested
    retrospective opens a thread and its audit **never feeds policy
    learning** until then;
  - `"primary_decides"` → the primary's `decide` role rules, **honoring
    the consensus points already agreed for that checkpoint** (they are
    passed into the call); the dissent stays on record as a verdict
    advisory and in the review record.

Every review is one auditable `REVIEW_COMPLETED` event, attached to its
journal record and rendered in the rationale dialog (outcome, rounds,
standing objections, agreed points).

## M30 — Ground-check RAG (`pgdca/security/grounding.py`)

**Inside the existing guardrails, optional.** A new rule kind for the
guardrail system — created, tiered, conditioned and weighted like any
other (HARD_BLOCK / SOFT_BLOCK / WARN / ADVISORY):

```json
{"kind": "ground_check", "attributes": ["unit_cost"],
 "tolerance": 0.15, "require_evidence": true}
```

**The knowledge store** is a deterministic local RAG: the system's own
**observations auto-index** (research results — the world is the best
ground truth) and the human adds curated documents (`KNOWLEDGE_ADDED`,
human-only over API/GUI — the system cannot launder self-asserted facts
into its own ground truth). Retrieval is lexical token-overlap,
dependency-free; an embedding retriever replaces it behind the same
interface in local deployment.

**The check** runs inside the supervisor with no LLM in the loop: a
decision whose claimed values contradict grounded facts (the advert's
`fruit @ 0.5` against the grounded `2.0`) triggers the guardrail
deterministically; `require_evidence` additionally flags confident
claims with no grounding at all. Defense in depth is visible in the
inbox: the injected purchase now carries both the ground-check reason
and the taint reason.

## Verification

121 tests green: the 107 from Phase 7 plus 9 review tests (off by
default, per-checkpoint granularity, consensus through defense rounds
with usage accounting, disagreement→human with enactment after
approval, disagreement→primary with agreed points honored and dissent
recorded, concession→withdrawal, strategy deferral + replanning pause +
resolution, contested retrospective blocking policy learning while
others learn, primary-mode retrospective still learning) and 5
grounding tests (observation auto-indexing + retrieval, human-only
knowledge, the advert lie caught by contradiction, ungrounded claims
flagged by require_evidence, grounded purchases passing clean). GUI
verified live via Playwright (double-defense inbox card, review line in
the rationale dialog, knowledge panel).
