"""PGDCA - Persistent Goal-Directed Cognitive Architecture.

Phase 0: Minimum Viable Loop, per the implementation specification
(docs/PGDCA_Cloud_Code_Implementation_Spec.md, Implementation Phases).

The event store is the single source of truth; everything else is a
projection. The LLM proposes; the controller governs; the Decision
Supervisor issues verdicts; Tier 1 guardrails are not writable by the
system identity.
"""

__version__ = "0.1.0"
