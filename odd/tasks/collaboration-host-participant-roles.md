# Add ephemeral collaboration roles and host removal

## Objective

Distinguish a live room host from participants and enforce the host's exclusive
permission to remove another participant without changing diagram editing rights.

## Problem and why

Collaboration currently exposes only join/leave peer IDs. The documented role
and permission requirement is therefore missing, and no server-side authority
check exists for participant removal.

## Authorized scope

- First active room connection is host; later connections are participants.
- Earliest remaining participant is promoted when the host disconnects.
- Host may remove another participant; the server verifies current authority.
- Presence state exposes ordered members and roles after membership changes.
- Add a minimal participant list with host/current-client labels and host-only removal.
- Update requirement status documentation and add focused backend/frontend tests.

Excluded: authentication, persistence, diagram CRUD restrictions, avatars,
cursors, editing presence, selections, chat, identity restoration, reconnection
redesign, and unrelated collaboration/signaling/WebRTC hardening.

## Constraints and decisions

- Sole writer; work on `develop` at `2e172067a4ffb5261878e02a9b05a0f87e1087f5`.
- Preserve the validated ICE buffering implementation and existing signaling payloads.
- No Docker, databases, new dependencies, commits, or pushes; GGA runs only on
  the final staged patch.
- Production role storage: the existing `channels_redis` group sorted set. Its
  join-time order defines host succession; an atomic Lua operation checks host
  authority and removes the target across workers. Empty groups have no role key.
- TDD mode: disabled by `docs/AI_CONTEXT.md`; use focused functional tests.
- Backend runner: `back_generador_bd/.venv/bin/python back_generador_bd/manage.py test collab.tests.test_roles`.
- Frontend runner: focused Angular/Karma specs for role state and participant UI.
- Delivery strategy: `ask-on-risk`; forecast is about 800 authored changed lines.
  No chain decision is needed in this work unit because the user prohibited commits.

## Tasks

- [x] **ROLE-1 — Enforce room roles and removal in Django Channels**
  - Acceptance: join order assigns host/participants; host-only removal is atomic
    and server-authorized; disconnect promotes the earliest remaining member;
    empty rooms reset; direct signaling remains compatible.
  - Checks: focused backend role/signaling tests.
  - Evidence: `collab.tests.test_roles` passed 5/5 after correcting one
    inverted test assertion; the tests cover assignment, denial, removal,
    promotion/state broadcast, empty-room reset, and unchanged direct signaling.

- [x] **ROLE-2 — Expose role state and add the minimal participants UI**
  - Acceptance: clients consume ordered presence state; host sees removal actions
    for other members; participants do not; promotion updates rendered state.
  - Checks: focused P2P role-state and participant-panel tests; TypeScript/build.
  - Evidence: new role-state and participant-panel specs passed 6/6; the
    combined role/UI plus existing ICE regression selection passed 12/12;
    TypeScript spec compilation and the production build passed. Build retained
    the existing bundle-budget/CommonJS warnings.

- [x] **ROLE-3 — Update traceability and verify scope**
  - Acceptance: gap matrix reflects implemented role/permission behavior; final
    diff contains no unrelated changes and records all failed/skipped checks.
  - Checks: final diff/status inspection.
  - Evidence: requirements now record the approved ephemeral role semantics;
    the gap matrix marks roles/permissions `DONE`; final inspection found 15
    related paths, about 790 authored changed lines, no staged files, and no
    whitespace or unrelated changes. A bounded real Redis-backed 3-client run
    confirmed first-host/later-participant assignment, ordered state convergence,
    participant removal denial, host kick and socket closure, longest-connected
    promotion, old-host rejoin as participant, shared-state recovery, and
    continued collaboration after kick/rejoin with no new regression.

## Progress and next step

All three tasks are implemented and verified by focused automation, independent
read-only review, and the bounded real Redis-backed 3-client runtime. One repair
attempt corrected an inverted test assertion; no implementation failure remained.
No commit, push, or Docker/database action was performed; GGA is handled by the
final staged-patch gate.
