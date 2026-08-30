"""Domain vocabulary: node kinds, relationship types, statuses.

The canonical relationship attributes and type semantics are normative
in Appendix A of the implementation specification. Numeric attributes
here use a 0..1 scale.
"""
from __future__ import annotations

from enum import Enum


class NodeKind(str, Enum):
    META_GOAL = "META_GOAL"
    PERSISTENT_GOAL = "PERSISTENT_GOAL"
    OBJECTIVE = "OBJECTIVE"
    TARGET = "TARGET"
    SUB_TARGET = "SUB_TARGET"
    TASK = "TASK"
    ACTION = "ACTION"
    FACTOR = "FACTOR"
    RESOURCE = "RESOURCE"
    TOOL = "TOOL"
    ACTOR = "ACTOR"
    POLICY = "POLICY"
    RISK = "RISK"
    ASSUMPTION = "ASSUMPTION"
    OPPORTUNITY = "OPPORTUNITY"
    EVIDENCE = "EVIDENCE"
    # exogenous inputs (M31): issued from outside the loop while it runs
    DIRECTIVE = "DIRECTIVE"   # normative human decision (target/constraint/context)
    FACT = "FACT"             # descriptive scenario change (imposed or opportunity)


# an ACTIVE directive is a propagation anchor: goal_effects, U(a),
# antagonisms and critique weigh it automatically via props.priority
GOAL_KINDS = {NodeKind.META_GOAL, NodeKind.PERSISTENT_GOAL, NodeKind.OBJECTIVE,
              NodeKind.DIRECTIVE}
RATIFICATION_KINDS = {NodeKind.META_GOAL, NodeKind.PERSISTENT_GOAL}
EXOGENOUS_KINDS = {NodeKind.DIRECTIVE, NodeKind.FACT}


class RelType(str, Enum):
    SUPPORT = "SUPPORT"
    ENABLE = "ENABLE"
    REQUIRED = "REQUIRED"
    BLOCK = "BLOCK"
    INHIBIT = "INHIBIT"
    RISK = "RISK"
    ANTAGONIZE = "ANTAGONIZE"
    DEPENDS_ON = "DEPENDS_ON"
    SUBSTITUTES = "SUBSTITUTES"
    AMPLIFIES = "AMPLIFIES"
    MITIGATES = "MITIGATES"
    CAUSES = "CAUSES"
    CORRELATES = "CORRELATES"
    DERIVES_FROM = "DERIVES_FROM"
    INVALIDATES = "INVALIDATES"
    SUPERSEDES = "SUPERSEDES"


POSITIVE_RELS = {RelType.SUPPORT, RelType.ENABLE, RelType.REQUIRED}
NEGATIVE_RELS = {RelType.BLOCK, RelType.INHIBIT, RelType.ANTAGONIZE, RelType.RISK}
CHAIN_RELS = {RelType.CAUSES}


class ValidationStatus(str, Enum):
    HYPOTHESIZED = "HYPOTHESIZED"
    OBSERVED = "OBSERVED"
    VALIDATED = "VALIDATED"


class NodeStatus(str, Enum):
    PROPOSED = "PROPOSED"       # awaiting human ratification (goals)
    ACTIVE = "ACTIVE"
    DEFERRED = "DEFERRED"
    SUSPENDED = "SUSPENDED"
    SUPERSEDED = "SUPERSEDED"
    INVALIDATED = "INVALIDATED"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


def node(id: str, kind: NodeKind, label: str, status: NodeStatus = NodeStatus.ACTIVE,
         review_interval: int = 3, **props) -> dict:
    return {
        "id": id,
        "kind": kind.value,
        "label": label,
        "status": status.value,
        "review_interval": review_interval,
        "props": props,
    }


def edge(id: str, src: str, dst: str, type: RelType,
         validation_status: ValidationStatus = ValidationStatus.HYPOTHESIZED,
         provenance: str = "design", **attrs) -> dict:
    return {
        "id": id,
        "src": src,
        "dst": dst,
        "type": type.value,
        "validation_status": validation_status.value,
        "validity_status": NodeStatus.ACTIVE.value,
        "provenance": provenance,
        "attrs": attrs,  # importance, cost, probability, confidence, substitutability, ...
    }
