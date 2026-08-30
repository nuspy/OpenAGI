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

Pre-implementation, revision **v1.1** applied (2026-08-30). The review recorded in `docs/ANALISI_E_PROPOSTE.md` approved items M1–M17 and M19–M20, rejected M21–M22, and added requirements M23–M28 (two-tier guardrails, decision supervisor, full GUI with separated frontend, interface-first tools, in-progress co-decision, importable skills/MCP servers). The rationale and the implementation spec carry the revision directly; the scientific paper carries it as **tracked changes** (author "Claude Code") to accept or reject in Word — rejecting all changes restores v1.0 exactly. Implementation starts from Phase 0 (Minimum Viable Loop) as defined in the spec.
