# Phase 2 — External-world connection points + strategy branching

## 1. Local-integration connection points (interface-first)

Everything that must be integrated on the owner's machine (the provider
library, CallAPICall, credentials-bound connectors) is deferred to
local development — **here only the ports exist**: typed Protocols,
mock adapters, conformance suites, and registry wiring. See
`docs/LOCAL_INTEGRATIONS.md` (operational guide, in Italian).

- `pgdca/ports/voice.py` — `VoiceCallPort` (CallAPICall point;
  spec §20 surface: initiate/answer/speak/listen/transcribe/
  detect_speaker_state/terminate).
- `pgdca/ports/messaging.py` — `EmailPort`, `SmsPort` with structured
  `MessageEvent`s.
- `pgdca/ports/browser.py` — `BrowserPort`; challenge pages are
  explicit states (never bypassed).
- `pgdca/ports/vault.py` — `VaultPort` + `IdentityPort`; handles only,
  never credentials; the identity conformance suite rejects adapters
  that return 2FA codes; the vault suite flags PAN-looking fields.
- `pgdca/tools/external.py` — `register_external_ports(...)`: with no
  local adapter each tool registers **DISABLED** ("pending local
  adapter") so the connection point is visible in the GUI without
  pretending the capability exists. Compliance lives in the wrappers,
  so no adapter can skip it: `voice.call` speaks the AI disclosure
  first (EU AI Act art. 50), `email.send` appends the honest-identity
  footer, `vault.pay` refuses without an authorization context,
  received content is labeled untrusted. Lifecycle conformance runs
  automatically on mocks only — on supplied (real) adapters it is
  side-effectful and must be run manually, as the integration guide
  instructs.
- Skeletons to fill on the local machine:
  `examples/adapters/local_llm_provider_adapter.py`,
  `examples/adapters/call_api_call_adapter.py`.

## 2. Strategy branching (spec: Hypothesis Engine / Strategy Branching)

Multi-step strategies with the full lifecycle
`PROPOSED → ACTIVE → DEFERRED / FAILED → SUCCESSFUL (+ PRUNED)`:

- the gateway role `strategies` proposes competing branches from
  graph-derived context only (external content never steers planning);
- `pgdca/planning.py` scores branches deterministically (front-loaded
  goal contribution with per-step discount, minus known cost), selects
  one, prunes dominated ones;
- the active branch guides arbitration through a small **adherence
  bonus** (default 0.05) — deliberately too small to overrule a
  genuinely better alternative, so the meeting opportunity still wins
  and produces an honest `STRATEGY_CHANGED` + replan instead of tunnel
  vision;
- satisfied steps and steps whose factor left the active context are
  skipped; step failures are tolerated up to a limit, then the branch
  FAILS; an executed off-plan action defers the branch; exhausted
  branches complete;
- decisions taken on-plan record their branch/step in the journal;
  branches persist as a projection (recovery-safe, replay-safe — the
  deterministic-replay test still passes with planning in the loop);
- GUI: the Policies tab shows the branch table (label, status,
  step k/n, score).

Observed in the base scenario: `critical-enablers-first` wins
selection, is followed for five steps, defers honestly when arbitration
prefers researching the substitute over buying unaffordable bars, and
the replanned branch completes. In the opportunity scenario the
deviation is the meeting ticket itself.

## Verification

63 tests green: the 51 from Phase 1 plus 8 port tests (conformance for
every mock, disabled-pending semantics, AI-disclosure-first, honest
footer, challenge surfacing, authorization-context requirement, no-2FA-
codes) and 4 strategy tests (proposal/selection/adherence, deviation +
replan, opportunity-driven strategy change, bonus bounded and recorded
in the journal). GUI strategy table and pending-port rows verified live
via Playwright.
