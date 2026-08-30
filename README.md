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

**Phase 1 implemented and green** (51 tests): persistent operation with recovery, imported skills and MCP servers under security gates (M28), Anthropic reference adapter behind the LLM port, dynamic reprioritization with target deferral — see [`docs/PHASE1.md`](docs/PHASE1.md). Phase 0 (Minimum Viable Loop) documented in [`docs/PHASE0.md`](docs/PHASE0.md) with the spec-traceability matrix. Documents at revision **v1.1** (2026-08-30): the review in `docs/ANALISI_E_PROPOSTE.md` approved M1–M17/M19–M20, rejected M21–M22, and added requirements M23–M28; the paper carries the revision as tracked changes (author "Claude Code") — rejecting all changes restores v1.0 exactly.

## Phase 0 quickstart

```bash
pip install -e ".[api,dev]"            # + ".[anthropic]" for the reference adapter
pytest                                 # 51 tests incl. acceptance scenarios + deterministic replay
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
  memory/                       journal, audit (dq≠oq), policies (SHADOW), calibration
  controller.py                 deterministic controller + cognitive cycle + recovery
  tools/                        registry, skill packages, MCP client, capability store
  scenario/                     toy acceptance scenario + opportunity reprioritization
  api/ ui/                      FastAPI backend + single-file web GUI
examples/                       sample skill package + sample MCP server
```
