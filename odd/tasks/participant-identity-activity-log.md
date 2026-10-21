# Add participant identity and shared activity log

## Objective

Add remembered anonymous display identities and a durable, shared activity feed
to the collaborative UML room without changing ephemeral role assignment or the
existing diagram operation protocol.

## Problem and why

The live room currently identifies members only by transient channel names and
shows synthetic `Usuario N` labels. Meaningful collaborative edits are relayed
but not recorded, so late joiners cannot see who performed important actions.

## Authorized scope

- Generate and remember a browser UUID token and display name with SSR/storage
  fallbacks, then send a backward-compatible `hello` after WebSocket open.
- Validate identity server-side and expose live names in presence snapshots.
- Persist participants and a strict whitelist of meaningful activity events;
  coalesce repeated text edits by the same connection and target/field for five
  seconds; never log movement, resizing, labels, vertices, or state sync.
- Add room activity history API and a live/history Angular activity panel.
- Preserve current host succession, kick authority, reconnect-as-new-connection,
  operation relay, ports, and deployment configuration.
- Add focused Django and Angular regression coverage and update traceability.

Excluded: accounts/authentication, AI/chat, viewer/mobile behavior, Spring,
Docker/Compose, environment files, dependency upgrades, ports, and unrelated
refactors.

## Constraints and decisions

- Work only in `feat/identidad-actividad`; leave all changes uncommitted and do
  not push, use Docker, start servers, or access network resources.
- TDD mode: disabled by `docs/AI_CONTEXT.md`; use focused functional tests.
- Backend WebSocket runner: `DJANGO_SECRET_KEY=test POSTGRES_PASSWORD=test /Users/pedroalaca/Projects/software1-final/back_generador_bd/.venv/bin/python back_generador_bd/manage.py test collab uml_api.tests.test_services_gemini`.
- Backend database runner: the focused activity model/API test label with
  `--settings=diagramador_uml.settings_test`.
- Frontend runners: `npx --no-install ng build` and
  `npx --no-install ng test --watch=false --browsers=ChromeHeadless --no-progress`.
- Production live-name storage uses a Redis hash adjacent to the existing role
  group; ORM work is isolated behind injectable stores so consumer tests remain
  database-free.
- Coalescing is connection-local using monotonic time. This exactly identifies
  a sender even when it never sent `hello`, and avoids merging separate anonymous
  clients with nullable actors.
- History/live event serialization is shared and includes an event ID so the
  frontend can merge race-prone REST and WebSocket delivery without duplicates.
- Delivery strategy: `ask-on-risk`; forecast is roughly 1,200 authored changed
  lines. No chain decision or work-unit commit applies because the user
  explicitly prohibited commits for this review worktree.
- Receipt-driven development remains disabled/unmanaged; ordinary checks apply.

## Tasks

- [ ] **I1-1 — Persist identity and meaningful activity in Django**
  - Acceptance: valid hello identities appear in every presence state, including
    late joins; invalid hello is ignored; legacy clients continue working;
    Participant/ActivityEvent schema and migration match the requested fields;
    only four operation types are logged and edit bursts coalesce; persistence
    failure never breaks operation relay or role/kick behavior.
  - Checks: focused database-free consumer tests plus existing collaboration tests.
  - Rollback: remove the new collab stores/models/migration and the bounded
    consumer integration while retaining the existing relay and role store.

- [ ] **I1-2 — Expose history and render identity/activity in Angular**
  - Acceptance: the room API returns capped oldest-to-newest history; browser
    identity survives storage when available and has stable memory fallback;
    participant names retain all current labels/actions; activity history and
    live events merge newest-first, render as text with relative time, and fail
    quietly when REST is unavailable.
  - Checks: focused model/API tests, identity/activity/presence Angular specs,
    and Angular production build.
  - Rollback: remove the activity endpoint/components/services and restore the
    optional-name participant rendering without touching diagram collaboration.

- [ ] **I1-3 — Verify regression safety and traceability**
  - Acceptance: requested Django/Angular suites are run where locally possible;
    known pre-existing Angular failures are distinguished from regressions; gap
    matrix and this document record exact results, skipped checks, and final
    uncommitted status.
  - Checks: requested full commands, `git diff --check`, final diff/status audit.
  - Rollback: documentation-only changes can be removed independently.

## Progress and next step

Exploration is complete. Current payloads only expose a class name on
`add_class`, so all other summaries must stay truthful and generic. Next:
implement I1-1 with injectable stores and database-free consumer coverage.
