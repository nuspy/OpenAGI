# OpenAGI — PGDCA

**Persistent Goal-Directed Cognitive Architecture (PGDCA)**: founding documents and design discussion.

PGDCA is a systems architecture in which a generative LLM operates as one component inside a deterministic executive control loop that maintains persistent goals, structured state, external memory, a causal factor graph, tool use, verification, auditing, and experience abstraction.

## Documents

| File | Content |
|---|---|
| [`docs/PGDCA_Scientific_Paper.docx`](docs/PGDCA_Scientific_Paper.docx) | Technical position paper / research proposal (source of truth; [Markdown mirror](docs/PGDCA_Scientific_Paper.md) generated for readability and diffs) |
| [`docs/PGDCA_Cognitive_Architecture_Design_Rationale.md`](docs/PGDCA_Cognitive_Architecture_Design_Rationale.md) | Design rationale — the reasoning, discoveries and architectural decisions behind PGDCA, written for implementation agents |
| [`docs/PGDCA_Cloud_Code_Implementation_Spec.md`](docs/PGDCA_Cloud_Code_Implementation_Spec.md) | Complete technical implementation specification |
| [`docs/ANALISI_E_PROPOSTE.md`](docs/ANALISI_E_PROPOSTE.md) | Analisi critica e proposte di modifica (in italiano) — attualmente in discussione, item per item |

## Status

**Phase 3 implemented and green** (72 tests): the metacognitive loop — counterfactual regret with the dq≠oq "bad luck ≠ bad judgment" distinction, a self-model that shrinks LLM-claimed success probabilities toward observed rates, recurrence advisories on previously-failed decision signatures, contradiction management (external claims never silently overwritten; observation beats claim, everything else human-only), macro-cycle pruning of stale hypothesized edges, and compensation of revoked executed actions — see [`docs/PHASE3.md`](docs/PHASE3.md). Earlier slices: [`docs/PHASE2.md`](docs/PHASE2.md) (typed external ports — voice/Call Happy Call, email, SMS, browser, vault, identity — mocks + conformance here, real adapters in local development per [`docs/LOCAL_INTEGRATIONS.md`](docs/LOCAL_INTEGRATIONS.md); strategy branching with full lifecycle), [`docs/PHASE1.md`](docs/PHASE1.md) (recovery, skills/MCP import M28, reference adapter, dynamic reprioritization), [`docs/PHASE0.md`](docs/PHASE0.md) (Minimum Viable Loop + spec-traceability matrix). Documents at revision **v1.1** (2026-08-30): the review in `docs/ANALISI_E_PROPOSTE.md` approved M1–M17/M19–M20, rejected M21–M22, and added requirements M23–M28; the paper carries the revision as tracked changes (author "Claude Code") — rejecting all changes restores v1.0 exactly.

## Quickstart

```bash
pip install -e ".[api,dev]"            # + ".[anthropic]" for the reference adapter
pytest                                 # 72 tests incl. acceptance scenarios + deterministic replay
python -m pgdca.scenario.toy           # scripted CLI demo (injection defense included)
python -m pgdca.scenario.opportunity   # dynamic reprioritization demo
python -m pgdca.api.server --db pgdca.db   # persistent backend + web GUI at http://127.0.0.1:8000
```

The event store is the single source of truth; the LLM proposes and the controller governs; the Decision Supervisor rules on every significant decision; Tier 1 guardrails are technically non-writable by the system identity; PAUSE/STOP are honored unconditionally; external content is data, never instructions.

```
pgdca/
  store.py runtime.py           event sourcing + deterministic replay
  domain.py graph.py            typed weighted causal graph (Appendix A schema)
  arbitration.py                canonical U(a), opportunity cost, sensitivity gate
  security/                     two-tier guardrails, decision supervisor, budgets, taint
  cognition/                    LLM gateway port + mock/replay/anthropic adapters
  memory/                       journal, audit (dq≠oq), policies (SHADOW), calibration,
                                self-model (calibrated priors), evidence/contradictions,
                                counterfactuals (regret, avoidability)
  planning.py                   strategy branching with lifecycle + adherence bonus
  controller.py                 deterministic controller + cognitive cycle + recovery
  ports/                        voice, email/SMS, browser, vault/identity (Protocol+mock+conformance)
  tools/                        registry, skill packages, MCP client, capability store, port wiring
  scenario/                     toy acceptance scenario + opportunity reprioritization
  api/ ui/                      FastAPI backend + single-file web GUI
examples/                       sample skill package, sample MCP server, local adapter skeletons
```
