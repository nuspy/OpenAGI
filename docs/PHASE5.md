# Phase 5 — Acquisition hardening (M10) + inference accounting (M13)

Acquired capability is the architecture's most dangerous input after
external content: code the system imports today runs inside its
authority tomorrow. This slice closes M10 ("sicurezza
nell'acquisizione di tool") and the remaining M13 items (cost
accounting per cognitive function, model routing).

## 1. Sandbox-first execution (`pgdca/tools/sandbox.py`)

Every MCP server process — and any future discovered/built tool — runs
under a `SandboxProfile`:

- **resource limits** via rlimits: CPU seconds (runaway loops die),
  address space, file size;
- **whitelisted environment**: only `PATH`/locale-class variables cross
  the boundary; credentials and session variables never reach acquired
  code (`PGDCA_SANDBOX=1` marks the context);
- **isolated working directory** (a private tempdir; file arguments are
  resolved before the move, relative paths in commands keep working);
- **wall-clock kill** of the whole process group.

Honest limits: OS-level network isolation is not portably achievable in
stdlib; it belongs to local deployment (bubblewrap/nsjail/containers)
and slots in behind this same profile without touching callers.

## 2. Provenance digests and pinning (`pgdca/tools/provenance.py`)

*What was reviewed is what runs.* Skill packages are digested
(`skill.json` + `SKILL.md`) at import; MCP server commands are pinned
over every file argument (entry scripts, local binaries). A command
with no file arguments reports itself honestly as `unpinned`.

## 3. Quarantine (`verify_all`)

`POST /api/capabilities/verify` (GUI: **Verify integrity**) — and
automatically **on every restart** during recovery — re-digests every
pinned capability. A mismatch quarantines it: disabled, status
`QUARANTINED` with the reason, all its registry tools disabled, and an
auditable `CAPABILITY_QUARANTINED` event carrying both digests
(actor: supervisor). A quarantined skill drops out of the LLM briefing
immediately. Nothing is silently re-imported; re-enabling is a human
act after review. The supply-chain test tampers a copied market server
(prices rewritten) and shows the tools going dark.

## 4. Human-gated promotion

Enabling any tool at `EXTERNAL_COMMUNICATION` or above is a human
decision (`set_tool_enabled`, `TOOL_UPDATED` events, per-tool toggles
in the GUI). The system may always *restrict* (disable) on its own —
the same asymmetry as Tier 2 guardrails.

## 5. LLM cost accounting per cognitive function (M13)

Inference is a budgeted resource. Every gateway call emits `LLM_USAGE`
(role, input/output tokens): real usage when the adapter reports it
(the Anthropic adapter attaches `response.usage`), otherwise a
deterministic size-based estimate — so deterministic replay stays
byte-identical. `LlmUsageProjection` aggregates per role
(`GET /api/llmusage`; Learning tab, "LLM usage per cognitive
function"), making it visible where the inference budget goes
(hypotheses vs critique vs strategies vs deliberation).

## 6. Model routing per role (M13)

`AnthropicLlmAdapter(model_by_role={...})` routes cognitive functions
to different models (e.g. a small model for critique-shaped
classification, the strongest for open reasoning), defaulting to the
adapter's main model. `Config.role_models` carries the mapping.

## Verification

94 tests green: the 82 from Phase 4 plus 12 hardening tests (runaway
kill, env whitelist, isolated cwd, digest recorded + clean verify,
tampered skill quarantined with supervisor-actor event, tampered MCP
server quarantined with tools disabled, sandboxed MCP call working,
quarantine surviving restart, human-gated risky enable, per-role usage
accounting matching the event stream, Anthropic per-role routing with
real usage attached, digest content-sensitivity). Deterministic replay
unaffected. Capabilities tab verified live via Playwright (quarantined
skill, pinned server, integrity button, per-tool toggles).
