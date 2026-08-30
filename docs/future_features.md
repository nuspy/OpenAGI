# Future features — a hierarchical / peer network of PGDCA instances

*Study document (requested with rev. 5). Nothing here is implemented;
the Phase 9 exogenous machinery is deliberately shaped so that this
future slots in without re-architecture.*

## 1. The vision

Today each PGDCA instance is independent: one human owner, one event
log, one graph. The next stage connects instances into a network with
three kinds of relations:

- **Superior → this instance**: a higher-level AI (a family
  coordinator, a team or company instance) issues **directives and
  facts from above** — priorities, constraints, context changes.
- **This instance → inferiors**: the instance propagates downward the
  decisions and facts *it* has settled (with its human), as directives
  and facts for subordinate instances.
- **Selected peers**: instances share facts and coordinate decisions
  laterally. The canonical example: *"voglio andare in vacanza"* — my
  AI coordinates with the AIs of my travel companions (align the
  dates) and notifies the AIs of the people in my projects of my
  unavailability (a shared fact).

## 2. Why Phase 9 is already the substrate

The design rule of Phase 9 was: **the network is not a new channel; it
is the same channel with a different envelope.**

- Every exogenous node carries an **`origin` envelope**:
  `{source, authority, instance}`. Today only
  `{"human_gui", "owner", "local"}` occurs; the network adds
  `{"network", "superior" | "peer" | "inferior_report", "<instance-id>"}`.
- The **trust rule is already live and tested**
  (`ExogenousManager._ingest_if_external`): any authority other than
  `owner` is *external content* — it is `CONTENT_INGESTED` (taint, M2),
  ground-checkable (M30), reviewable (M29), its node is never
  auto-active, its integration **always** requires the local human's
  consensus thread. A peer fact behaves exactly like an untrusted web
  page that happens to arrive structured.
- The **integration pipeline** (propose → optional cross-AI review →
  human thread → weave) is the single entry point, so network inputs
  inherit every defense the moment they exist.
- **Deliberation threads** are the natural surface where upstream
  directives are discussed before adoption; **change-set ops** are the
  transactional unit a resolution applies — both already exist.

## 3. Authority model

| Relation | What arrives | Default treatment |
|---|---|---|
| owner (local human) | directives, facts, ops | trusted; imposed facts active on arrival; consensus threads for weaving |
| superior | directives, facts | PROPOSED + external pipeline; weight suggests priority, the **local human ratifies** |
| peer | facts (incl. opportunities), coordination requests | PROPOSED + external pipeline; opportunities accepted/declined locally |
| inferior | reports (outcomes, facts observed below) | evidence/claims (M17 evidence store), never directives |

**Non-negotiable, carried over from the constitution**: the local
human's Tier 1 guardrails, the budget ratchet, and STOP/PAUSE are
**never delegable upward**. A superior's directive can carry any
weight; it cannot write Tier 1, cannot raise budgets, cannot suppress
corrigibility. For enterprise deployments where upstream *should* be
authoritative in practice, the pattern is a **policy bridge**: the
local human ratifies upstream directive classes in batch (a standing
Tier 1 guardrail authored locally that says "auto-confirm integration
threads from instance X below weight w") — authority is *granted
locally and revocably*, never assumed by the network.

## 4. Outbound: what this instance shares

- **Publish set**: nodes gain a `visibility` field —
  `private` (default) | `shared:{instance ids}` | `public-to-network`.
  Only ACTIVE, human-ratified nodes are shareable; the human marks them
  (a "Share" action in World inputs).
- **Downward directives**: the instance composes a directive for
  inferiors *only from an integration the human confirmed* — the
  outbound artifact cites the local thread id (provenance chain).
- **Peer coordination**: a coordination request is a fact-opportunity
  pair — my instance sends "vacation dates X–Y proposed" as an
  opportunity fact to each companion's instance; their humans accept or
  decline; the accepted set comes back as facts that weave into my
  plan. Unavailability notices to project peers are plain shared facts.

## 5. Protocol sketch

- **Transport**: MCP server-to-server is the natural candidate — each
  instance exposes an MCP server with `receive_directive`,
  `receive_fact`, `receive_report` tools; the M10 sandbox + provenance
  pinning already govern imported connectors.
- **Envelope, signed**: `{payload, origin, hop_chain, signature}` —
  Ed25519 per instance; authority claims are verified against a locally
  configured key registry (the human pairs instances explicitly, like
  Bluetooth). **Authority spoofing dies here**: an unverifiable
  "superior" claim downgrades to peer-untrusted.
- **Idempotent event exchange**: nodes/updates carry
  `(instance, node_id, version)`; re-delivery is a no-op; retirement
  propagates as an update, mirroring the local retire-cascade.
- **Anti-loop**: `hop_chain` of instance ids; an instance drops
  anything already carrying its id; a hop budget caps depth.
- **Privacy**: only the fact's label/weight/typed relations travel —
  never the local journal, budgets, or graph; per-peer redaction
  profiles.

## 6. Failure modes and mitigations

| Failure | Mitigation |
|---|---|
| Authority spoofing | signed envelopes + local key pairing; unverified ⇒ peer-untrusted |
| Injection via peer facts | already-live external pipeline: taint, ground-check, consensus, review |
| Directive oscillation (contradictory upstream inputs) | integration threads detect conflicts (the M32 consultation on directive conflicts); the human is the fixed point |
| Consensus drift (network "agrees" itself into nonsense) | every instance's constitution is local; cross-AI review with a *different* model family per instance keeps correlated failure down |
| Runaway propagation | hop budget + idempotency + visibility defaulting to private |
| Corrigibility erosion | STOP/PAUSE/Tier 1/budget ratchet are local-only by construction; no network message type can touch them |

## 7. Roadmap (not now)

1. **N1 — wire format + key pairing**: envelope schema, signature
   verification, the MCP receive tools feeding
   `issue_directive`/`record_fact` with network origins (the code path
   already exists; N1 is transport + crypto).
2. **N2 — outbound sharing**: visibility field, Share action, the
   fact/opportunity coordination pair, provenance chains on downward
   directives.
3. **N3 — policy bridge**: locally-authored standing ratification for
   trusted upstream classes; audit dashboards for network traffic.
4. **N4 — federation bench**: extend PGDCA-Bench with a two-instance
   scenario (a spoofed superior, a lying peer, a legitimate
   coordination) and measure resistance/uptake exactly like M20.
