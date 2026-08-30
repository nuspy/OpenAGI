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

    # --- policy learning guardrails ---
    policy_min_evidence: int = 2          # independent supporting episodes before a policy is created
    policy_min_decision_quality: float = 0.7
    policy_activation_agreements: int = 3  # shadow agreements required before ACTIVE

    # --- calibration / apprentice mode ---
    calibration_min_samples: int = 3
    calibration_poor_brier: float = 0.25  # mean Brier above this = poorly calibrated domain

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

    extra: dict = field(default_factory=dict)
