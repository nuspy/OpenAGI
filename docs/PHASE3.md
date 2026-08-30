# Phase 3 — Metacognition: counterfactuals, evidence, self-model

Six mechanisms that close the metacognitive loop: the system now judges
its own judgment, keeps external claims honest, shrinks its optimism
toward observed reality, warns itself about repeating mistakes, prunes
its own speculative graph edges, and can undo what the human revokes.

## 1. Counterfactual analysis (M6/M8 — audit deepening)

After every outcome audit, `pgdca/memory/counterfactual.py` re-reads the
decision's recorded alternatives and computes:

- `realized` — the utility actually obtained (the decision's score on
  success, minus the normalized cost on failure);
- `regret = max(0, best_alternative_utility − realized)` — an estimate,
  flagged as such (`estimate: true`), since the road not taken was never
  observed;
- `avoidable` — true only when the action failed **and** a
  better-scored alternative existed at decision time. The helmet
  stockout is the canonical negative case: the purchase was the
  best-scored option, so the failure is bad luck, not bad judgment —
  `avoidable: false`, consistent with the dq≠oq doctrine.

Emitted as `COUNTERFACTUAL_ANALYZED`, attached to the journal record,
and shown in the rationale packet (GUI decision dialog).

## 2. Self-model with calibrated priors (M6, M9 — apprentice discipline)

`pgdca/memory/selfmodel.py` tracks attempts/successes per
`domain/action`. Every hypothesis' claimed success probability is
shrunk toward the observed rate before arbitration:

```
calibrated = (claimed·k + successes) / (k + attempts)      k = 3
```

The LLM's original claim is preserved as
`params.claimed_success_prob` for audit; the decision carries the
calibrated value. With no history the claim passes through unchanged
(pseudo-count shrinkage, no cold-start distortion); after the helmet
failure, later purchase decisions demonstrably carry `success_prob <
claimed` — earned optimism, not presumed.

## 3. Recurrence advisories (M8 — anti-repetition)

Decision signatures (the same abstraction the policy engine uses) accum-
ulate success/failure counts. When a signature has failed at least
`recurrence_failure_threshold` (2) times, the supervisor's verdict for
the next matching decision carries an `[advisory] … previously failed`
reason — advisory-weight, never a block: it informs the human (inbox,
journal) without letting outcome luck veto a sound decision class.

## 4. Contradiction management (M17 — memory hygiene)

`pgdca/memory/evidence.py` records external claims as first-class
evidence (`CLAIM_RECORDED`, trust level `external`). When an
observation from an authoritative tool disagrees (the advert's
`fruit @ 0.5` vs the market's `2.0`), a `CONTRADICTION_DETECTED` event
is emitted and the pair is stored — **claims are never silently
overwritten**. One auto-resolution exists: direct observation beats an
external claim (`RESOLVED_B`). Every other resolution (context-
dependent, both-wrong, …) is human-only — the system identity gets a
`PermissionError`, same enforcement pattern as Tier 1 guardrails.
GUI: Learning tab, Contradictions panel; API
`POST /api/contradictions/{id}/resolve`.

## 5. Macro-cycle graph hygiene (M7 — anti-hallucination)

Every `macro_interval_cycles` (10) the reconciler prunes HYPOTHESIZED
edges that survived `hypothesized_edge_ttl` (8) cycles without
validation: each is marked `INVALIDATED` (`EDGE_UPDATED`) and the sweep
is summarized in one `GRAPH_MAINTENANCE` event. Validated design edges
are untouchable by this path. Speculative model inferences therefore
have a bounded lifetime unless evidence arrives.

## 6. Compensation on revoked executions (M24 — supervisor override)

Revoking an **already-executed** verdict from the GUI now does more
than record dissent: the controller looks up a `compensate.<action>`
tool (the toy market registers `compensate.purchase` → refund),
executes it under the same registry discipline, emits a negative
`RESOURCE_SPENT` (budget restored), decrements `acquired_qty`, and
records `COMPENSATION_EXECUTED` in the journal record. If no
compensation tool exists the revocation still stands, honestly marked
uncompensated.

## Verification

72 tests green: the 63 from Phase 2 plus 9 metacognition tests
(regret/avoidability incl. the bad-luck case, advert contradiction →
`RESOLVED_B`, human-only resolution, calibrated shrinkage formula, the
live loop using calibrated priors with the claim preserved, recurrence
advisory surfacing in a verdict, macro hygiene pruning `e_wild_guess`
while design edges survive, compensation restoring the budget to zero
spent, repeated environment failures accumulating recurrence). The
deterministic-replay acceptance test still passes with all six
mechanisms in the loop. The Learning tab (strategies, policies,
self-model, contradictions) verified live via Playwright.
