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

**Phase 6 implemented and green** (100 tests): PGDCA-Bench (M20), the falsifiability slice — a seeded multi-day environment (competing goals, persistent stockouts, a legitimate discount and an adversarial injection both arriving through untrusted channels), a verify-then-approve human oracle, ablation conditions at equal scenario, and operationalized metrics computed from the event log. Baseline: injection resistance 1.0 → 0.0 without the taint defense, opportunity uptake 1.0 everywhere, budget/STOP compliance 15/15, ~79% more tokens per target without calibrated priors — see [`docs/BENCH_BASELINE.md`](docs/BENCH_BASELINE.md) and [`docs/PHASE6.md`](docs/PHASE6.md). Earlier slices: [`docs/PHASE5.md`](docs/PHASE5.md) (M10 sandbox/provenance/quarantine + M13 usage accounting and model routing), [`docs/PHASE4.md`](docs/PHASE4.md) (Deliberation M27: co-decision threads with evidence-grounded answers, binding human-only outcomes, escalation-as-thread, dissent advisories, SSE-live console), [`docs/PHASE3.md`](docs/PHASE3.md) (counterfactual regret with the dq≠oq "bad luck ≠ bad judgment" distinction, calibrated self-model, recurrence advisories, contradiction management, graph hygiene, compensation), [`docs/PHASE2.md`](docs/PHASE2.md) (typed external ports — voice/Call Happy Call, email, SMS, browser, vault, identity — mocks + conformance here, real adapters in local development per [`docs/LOCAL_INTEGRATIONS.md`](docs/LOCAL_INTEGRATIONS.md); strategy branching with full lifecycle), [`docs/PHASE1.md`](docs/PHASE1.md) (recovery, skills/MCP import M28, reference adapter, dynamic reprioritization), [`docs/PHASE0.md`](docs/PHASE0.md) (Minimum Viable Loop + spec-traceability matrix). Documents at revision **v1.1** (2026-08-30): the review in `docs/ANALISI_E_PROPOSTE.md` approved M1–M17/M19–M20, rejected M21–M22, and added requirements M23–M28; the paper carries the revision as tracked changes (author "Claude Code") — rejecting all changes restores v1.0 exactly.

## Quickstart

```bash
pip install -e ".[api,dev]"            # + ".[anthropic]" for the reference adapter
pytest                                 # 100 tests incl. acceptance scenarios + deterministic replay
python -m pgdca.bench --seeds 5 --days 6   # PGDCA-Bench: seeded metrics + ablations (M20)
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
  collaboration/                deliberation threads (co-decision, escalation-as-thread)
  controller.py                 deterministic controller + cognitive cycle + recovery
  ports/                        voice, email/SMS, browser, vault/identity (Protocol+mock+conformance)
  tools/                        registry, skill packages, MCP client, capability store, port wiring,
                                sandbox (rlimits/env-whitelist), provenance digests + quarantine
  scenario/                     toy acceptance scenario + opportunity reprioritization
  bench/                        PGDCA-Bench: seeded multi-day world, metrics, ablations
  api/ ui/                      FastAPI backend + single-file web GUI
examples/                       sample skill package, sample MCP server, local adapter skeletons
```
