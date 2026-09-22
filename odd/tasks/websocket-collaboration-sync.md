# Route UML collaboration operations through WebSocket

## Objective

Move live UML create, update, delete, move, and full-state synchronization from
WebRTC `RTCDataChannel` to the existing Django Channels WebSocket broadcast
path while preserving the current JointJS event model and WebRTC signaling.

## Problem

The deployed WebSocket connects successfully, but UML operations are sent only
through browser-to-browser RTC data channels. When no data channel is open,
`sendToAll` silently drops operations. The initial full-state request also runs
before collaboration transport is ready, while `RTCDataChannel.onopen` invokes
the request locally instead of sending it to the room.

## Why

The existing `CanvasConsumer` already relays room broadcasts through the Redis
channel layer. Reusing that path is the smallest reliable Priority 0 fix for the
2-3 user EC2 deployment and avoids a WebRTC/TURN redesign.

## Authorized scope

- `odd/tasks/websocket-collaboration-sync.md`
- `front_generador_bd/src/services/colaboration/p2p.service.ts`
- `front_generador_bd/src/services/colaboration/collaboration.service.ts`
- `front_generador_bd/src/services/diagram/diagram.service.ts`
- `front_generador_bd/src/services/colaboration/p2p.websocket-sync.spec.ts`
- `front_generador_bd/src/services/colaboration/collaboration.service.spec.ts`
- `back_generador_bd/collab/tests/test_roles.py`

## Explicit exclusions

- Do not modify `back_generador_bd/collab/consumers.py`.
- Do not modify `signaling.service.ts`.
- Do not change persistence, CORS, stale-user cleanup, or kick lifecycle.
- Do not rewrite or remove existing WebRTC offer/answer/ICE signaling.
- Do not commit until the user reviews the diff.

## Constraints and rationale

- Keep `P2PService.sendToAll` as the public call boundary to minimize churn,
  but route its payload through `SignalingService.broadcast`.
- Continue using WebRTC for its existing negotiation path; UML operations must
  no longer be emitted through `RTCDataChannel.send`.
- Ignore the server's broadcast echo from the current channel to avoid applying
  local operations twice.
- Start room-state recovery only after the server has assigned the local
  channel identity, so the full-state request is sent over an open WebSocket.
- Preserve all JointJS event handlers and remote-operation application logic.

## Test mode

- TDD: disabled.
- Source: `docs/AI_CONTEXT.md` states strict TDD is disabled.
- Backend runner: `docker exec django_backend_UML python manage.py test collab.tests.test_roles`.
- Frontend runner: Angular/Karma focused specs with `--watch=false` and
  `ChromeHeadless`.
- Ordinary verification remains required.

## Delivery

- Strategy: `ask-on-risk`.
- Forecast: approximately 180-260 authored changed lines, generated files
  excluded; below the 400-line chaining threshold.
- RDD: disabled/unmanaged; no review run will be started.
- Commit: user approved the work-unit commit after reviewing the complete diff.

## Tasks

- [x] **WS-1 — Route UML operations and full-state requests through room broadcasts**
  - Change the frontend data path without modifying JointJS handlers or the
    Django consumer.
  - Remove the premature initialization request and the DataChannel-local
    full-state trigger.
  - Acceptance: local operations are emitted with WebSocket broadcast;
    remote room broadcasts reach `CollaborationService`; sender echoes do not.
  - Checks: focused frontend specs and TypeScript compilation.

- [x] **WS-2 — Prove the existing Django room broadcast relay**
  - Extend the focused Channels communicator suite with unchanged-payload and
    room-delivery coverage.
  - Acceptance: the existing consumer relays a UML operation through the group
    to another client without source changes.
  - Checks: `collab.tests.test_roles`.

- [x] **WS-3 — Verify the bounded work unit**
  - Confirm only authorized files changed.
  - Show the complete Git diff.
  - Run the focused tests and verify no production call to
    `RTCDataChannel.send` remains for UML operations.
  - Report the known Priority 0 limitations.

## Progress

- Approved by the user on 2026-09-21.
- Feature branch: `fix/websocket-collaboration-sync` from `033747f`.
- UML operations now use `SignalingService.broadcast`; production collaboration
  code contains no `RTCDataChannel.send` call.
- Full-state recovery starts after the server assigns the local channel ID.
- The existing Django consumer was left unchanged and its room relay was
  covered with a Channels communicator test.
- Seven authorized paths are changed; no excluded path is modified.
- Work-unit commit identity: `fix: route UML collaboration through WebSocket`
  (the commit containing this task document and its implementation).

## Verification evidence

- Focused frontend collaboration suite: 15/15 passed.
- New frontend WebSocket/full-state specs: 6/6 passed.
- Backend `collab.tests.test_roles`: 6/6 passed.
- `npx tsc -p tsconfig.spec.json --noEmit`: passed.
- Angular production build with `NG_BUILD_MAX_WORKERS=1`: passed with only the
  existing bundle-budget and CommonJS warnings.
- `git diff --check`: passed.
- Static transport check found UML operations flowing through
  `CollaborationService.broadcast` -> `P2PService.sendToAll` ->
  `SignalingService.broadcast`, with no production `dc.send` call.
- Initial sandboxed Angular test/build attempts exited 134 while launching the
  Angular toolchain; both passed when rerun with the established unsandboxed
  Chrome/build execution.
- Runtime browser/EC2 harness: not run in this work unit; deployment remains a
  separate user-controlled step.
- Rollback boundary: revert the six source/test paths listed above; the task
  document can be removed independently. No persistence or backend consumer
  behavior is coupled to this change.

## Next step

Report the created work-unit commit identity and leave push/merge decisions to
the user.
