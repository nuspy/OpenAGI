"""Cross-AI review (M29): a second, independent AI reviews sensitive
outputs of the primary before they are enacted.

Optional and granular: `Config.review_matrix` holds, per checkpoint
("decision", "strategy", "retrospective"), whether review is enabled,
the maximum number of interactions allowed to reach consensus, and the
disagreement override - "human" (the final decision is discussed with
the human before being enacted) or "primary_decides" (the primary AI
decides in the end, honoring the consensus points already agreed for
that checkpoint). The matrix is runtime-editable like every Config
field (Config tab / POST /api/config).

Mechanics are deterministic; only the wording is generative. The
reviewer is any `LlmPort` adapter behind its own gateway, so every
exchange is logged (LLM_REQUEST/RESPONSE/USAGE), replayable and
cost-accounted like primary cognition. Round shape:

    reviewer "review"  -> objections in `risks` (empty = agree)
    primary  "defend"  -> maintained points in `risks`
                          (empty = the primary concedes: WITHDRAWN),
                          accepted points in `assumptions`

Outcomes: CONSENSUS · WITHDRAWN (primary conceded - not enacted) ·
DISAGREEMENT_HUMAN · DISAGREEMENT_PRIMARY (with a final "decide" call
citing the accumulated agreed points). Every review is one auditable
REVIEW_COMPLETED event attached to its journal record.
"""
from __future__ import annotations

from ..config import Config
from ..events import Actor, Ev, Event
from ..security.supervisor import RISK_ORDER


class ReviewProjection:
    def __init__(self):
        self.reviews: dict[str, dict] = {}
        self.order: list[str] = []
        self.by_subject: dict[str, list[str]] = {}
        self.agreed_points: dict[str, list[str]] = {}   # checkpoint -> points

    def apply(self, ev: Event) -> None:
        if ev.type != Ev.REVIEW_COMPLETED.value:
            return
        r = ev.payload.get("review")
        if not isinstance(r, dict) or "id" not in r:
            return
        self.reviews[r["id"]] = r
        self.order.append(r["id"])
        sid = r.get("subject_id")
        if sid:
            self.by_subject.setdefault(sid, []).append(r["id"])
        pts = self.agreed_points.setdefault(r["checkpoint"], [])
        for p in r.get("agreed_points", []):
            if p not in pts:
                pts.append(p)

    def for_subject(self, subject_id: str) -> list[dict]:
        return [self.reviews[i] for i in self.by_subject.get(subject_id, [])]

    def snapshot(self) -> list[dict]:
        return [self.reviews[i] for i in self.order]


class ReviewEngine:
    def __init__(self, runtime, projection: ReviewProjection,
                 primary_gateway, review_gateway,
                 config: Config | None = None):
        self.runtime = runtime
        self.projection = projection
        self.primary = primary_gateway
        self.review_gateway = review_gateway
        self.config = config or Config()

    def policy(self, checkpoint: str) -> dict:
        p = self.config.review_matrix.get(checkpoint)
        return p if isinstance(p, dict) else {}

    def review(self, checkpoint: str, subject: dict,
               context: dict | None = None) -> dict:
        policy = self.policy(checkpoint)
        if not policy.get("enabled"):
            return {"outcome": "skipped"}
        if checkpoint == "decision":
            min_rc = policy.get("min_risk_class", "FINANCIAL")
            if (RISK_ORDER.get(subject.get("risk_class", "READ_ONLY"), 0)
                    < RISK_ORDER.get(min_rc, 0)):
                return {"outcome": "skipped"}
        context = context or {}
        max_rounds = max(1, int(policy.get("max_rounds", 2)))
        messages: list[dict] = []
        agreed: list[str] = []
        outcome = None
        rounds = 0
        standing: list[dict] = []
        for rnd in range(1, max_rounds + 1):
            rounds = rnd
            rev = self.review_gateway.ask("review", {
                "checkpoint": checkpoint, "subject": subject,
                "review_context": context,
                "prior_agreed_points":
                    self.projection.agreed_points.get(checkpoint, [])[-10:],
                "exchange": messages})
            messages.append({"author": "reviewer", "round": rnd,
                             "text": rev.summary, "objections": rev.risks})
            agreed.extend(rev.assumptions)
            standing = rev.risks
            if not rev.risks:
                outcome = "consensus"
                break
            if rnd == max_rounds:
                break   # interactions exhausted with standing objections
            defense = self.primary.ask("defend", {
                "checkpoint": checkpoint, "subject": subject,
                "objections": rev.risks, "review_context": context,
                "exchange": messages})
            messages.append({"author": "primary", "round": rnd,
                             "text": defense.summary,
                             "maintained": defense.risks})
            agreed.extend(defense.assumptions)
            if not defense.risks:
                outcome = "withdrawn"   # the primary conceded: do not enact
                break
        if outcome is None:
            mode = policy.get("on_disagreement", "human")
            if mode == "primary_decides":
                final = self.primary.ask("decide", {
                    "checkpoint": checkpoint, "subject": subject,
                    "standing_objections": standing,
                    "review_context": context,
                    "agreed_points":
                        self.projection.agreed_points.get(checkpoint, [])})
                messages.append({"author": "primary", "round": rounds,
                                 "text": final.summary, "final": True})
                outcome = "disagreement_primary"
            else:
                outcome = "disagreement_human"
        record = {
            "id": self.runtime.next_id("rvw"),
            "checkpoint": checkpoint,
            "subject_id": subject.get("id") or subject.get("decision_id"),
            "outcome": outcome, "rounds": rounds,
            "messages": messages,
            "agreed_points": sorted(set(agreed)),
            "standing_objections": standing if outcome.startswith("disagree")
            else [],
        }
        payload = {"review": record}
        if record["subject_id"] and (checkpoint in ("decision", "retrospective")):
            payload["decision_id"] = (subject.get("decision_id")
                                      or subject.get("id"))
        self.runtime.emit(Ev.REVIEW_COMPLETED, payload, Actor.SYSTEM)
        return self.projection.reviews[record["id"]]
