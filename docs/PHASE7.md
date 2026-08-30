# Phase 7 — Console completion (M25 remainder, M17 residual)

The last explicitly requested GUI surfaces from the rev. 2 requirements
("gui di configurazione", "definizione di target primario e secondari:
ogni componente deve avere una gui"), plus operator identity and
attention hygiene.

## 1. Configuration GUI (M25e)

Every `Config` threshold is now editable at runtime from the **Config**
tab. `Controller.update_config` is human-only, type-coerces against the
field's current type, rejects unknown fields, and emits a
`CONFIG_UPDATED` event — auditable and **reapplied on recovery**, so a
tuned system restarts tuned. The Config object is shared by reference
with every projection, so a change (a taint window, an adherence bonus,
the macro cadence, `role_models`) takes effect on the next cycle.
API: `GET/POST /api/config`.

## 2. Goal definition and ratification GUI (M25c)

The Graph tab gains a **New goal** form (kind, label, priority →
`GOAL_PROPOSED`, status PROPOSED, dashed in the graph) and the node
detail shows a **Ratify** button for proposed meta/persistent goals —
the M1 contract ("the system proposes, the human ratifies") now has its
one-click surface. Ratification stays human-only at the controller
(403 for the system identity over the API).

## 3. Operator identity

The header's **operator name** field (persisted per browser) travels as
`X-User` and is stamped into the notes of human decisions —
`"ok [by alice]"` on pending resolutions and overrides — so the journal
records *who* decided, not just that a human did. This is the honest
minimal step before real authentication (which stays a local-deployment
concern, like the rest of the identity surface).

## 4. Attention hygiene (M17 residual)

External content now leaves the LLM briefing after
`external_content_context_cycles` (default 6) cycles: the working
context stops growing with every advert ever seen, and stale
manipulative text loses its audience. The event log keeps everything —
audit, replay and the taint tracker are unaffected. A side effect worth
naming: this *shrinks the injection attack window* on its own. The
bench pins a huge window for its world (a persistent adversary by
construction), so its metrics keep measuring the defense layers rather
than this cutoff.

## Verification

107 tests green: the 100 from Phase 6 plus 7 console tests (human-only
config editing with type coercion and shared-reference propagation,
unknown/invalid fields rejected atomically, config surviving restart,
config API including 403/404 paths, goal proposal + system-ratify-403 +
human ratification over the API, operator stamped into override notes,
old content leaving the briefing while log and taint tracker keep it).
Config tab verified live via Playwright.
