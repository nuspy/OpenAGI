"""Central configuration for the Phase 0 loop.

Every threshold that shapes cognitive behavior lives here so tests and
operators can tune it; nothing is hard-coded into prompts or the LLM.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Config:
    # --- arbitration (canonical U(a), Appendix A of the spec) ---
    cost_weight: float = 0.4          # weight of normalized direct cost in U(a)
    risk_weight: float = 1.0          # weight of risk-adjusted cost
    oc_weight: float = 0.5            # weight of opportunity cost
    ig_weight: float = 0.5            # weight of expected information gain
    unaffordable_penalty: float = 1.0  # dominates U(a) when cost exceeds remaining budget

    # --- sensitivity gate (calibrated-scoring discipline) ---
    low_confidence_threshold: float = 0.6   # inputs below this are perturbed
    perturbation: float = 0.3               # +/- relative perturbation of low-confidence inputs

    # --- prompt-injection taint tracking ---
    taint_window_cycles: int = 2      # cycles during which external ingestion taints high-impact actions
    external_content_context_cycles: int = 6  # attention hygiene: older external content leaves the LLM briefing (events keep it)

    # --- policy learning guardrails ---
    policy_min_evidence: int = 2          # independent supporting episodes before a policy is created
    policy_min_decision_quality: float = 0.7
    policy_activation_agreements: int = 3  # shadow agreements required before ACTIVE

    # --- calibration / apprentice mode ---
    calibration_min_samples: int = 3
    calibration_poor_brier: float = 0.25  # mean Brier above this = poorly calibrated domain

    # --- self-model: calibrated success priors (claims shrink toward observation) ---
    calibration_pseudo_count: int = 3     # weight of the LLM's claimed probability
    recurrence_failure_threshold: int = 2  # past failures before an advisory fires
    dissent_advisory_threshold: int = 1   # human deliberation dissents before an advisory fires

    # --- deliberation (human-AI co-decision threads) ---
    deliberation_history_window: int = 6  # recent messages passed to the gateway

    # --- macro-cycle maintenance ---
    macro_interval_cycles: int = 10       # full-sweep maintenance cadence
    hypothesized_edge_ttl: int = 8        # cycles before an uncorroborated edge is pruned

    # --- causal propagation guardrails ---
    max_propagation_depth: int = 2
    hypothesized_edge_penalty: float = 0.6  # confidence multiplier for HYPOTHESIZED edges

    # --- strategy branching ---
    strategy_adherence_bonus: float = 0.05   # small: real re-arbitration must still win
    strategy_prune_ratio: float = 0.5        # branches below best*ratio are pruned
    strategy_step_discount: float = 0.85     # front-loaded value in branch scoring
    strategy_max_step_failures: int = 2      # step failures before a branch FAILS

    # --- loop limits (bounded autonomy: hard ceilings, human-expandable only) ---
    max_cycles_per_run: int = 50

    # --- LLM gateway ---
    gateway_max_repairs: int = 1
    role_models: dict = field(default_factory=dict)  # cognitive function -> model id (M13 routing)

    # --- cross-AI review (M29): optional + granular per checkpoint ---
    # max_rounds = interactions allowed to reach consensus; on exhaustion
    # on_disagreement decides: "human" (discuss with the human before
    # enacting) or "primary_decides" (the primary AI decides, honoring
    # the consensus points already agreed for that checkpoint)
    review_matrix: dict = field(default_factory=lambda: {
        "decision": {"enabled": False, "max_rounds": 2,
                     "on_disagreement": "human",
                     "min_risk_class": "FINANCIAL"},
        "strategy": {"enabled": False, "max_rounds": 2,
                     "on_disagreement": "human"},
        "retrospective": {"enabled": False, "max_rounds": 1,
                          "on_disagreement": "primary_decides"},
        "integration": {"enabled": False, "max_rounds": 1,
                        "on_disagreement": "human"},
    })

    # --- exogenous inputs (M31) + AI-initiated consultations (M32) ---
    exogenous_require_consensus: bool = True   # integration waits for the human thread
    exogenous_auto_weave_below: float = 0.0    # below this weight, edges self-apply as HYPOTHESIZED
    consultation_interval_cycles: int = 0      # 0 = off; else a periodic sync thread opens

    # --- autonomous target decomposition (human-consensus weave) ---
    decomposition_enabled: bool = True         # unfed targets get a breakdown proposal
    decomposition_max_per_cycle: int = 1       # LLM cost control

    # --- product scouting (real options -> owner's choice -> payment) ---
    scouting_enabled: bool = True              # buy-targets get real options (needs browser)
    scouting_max_per_cycle: int = 1
    scouting_max_pages: int = 3                # browser fetches per scouting

    # --- capability-acquisition sandbox (M10) ---
    sandbox_cpu_seconds: int = 10
    sandbox_memory_bytes: int = 512 * 1024 * 1024
    sandbox_wall_seconds: float = 15.0

    extra: dict = field(default_factory=dict)
