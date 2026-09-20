# Buffer early WebRTC ICE candidates

## Objective

Prevent ICE candidates received before a peer's remote SDP is installed from being discarded.

## Problem and why

The collaboration signaling path currently calls `addIceCandidate()` while
`remoteDescription` can still be `null`. The resulting `InvalidStateError` is
caught, but the candidate is lost and the peer can remain disconnected.

## Authorized scope

- Add a per-peer FIFO pending ICE buffer in `P2PService`.
- Flush it after successful offer and answer remote-description installation.
- Clear pending ICE when all peers are closed/reset.
- Add focused unit coverage for early, ordered, immediate, and exactly-once handling.

Explicitly excluded: self-peer filtering, `request_full_state`, zombie cleanup,
signaling serialization, reconnection redesign, Docker, databases, GGA, commits,
and pushes.

## Constraints and decisions

- Preserve public APIs and unrelated collaboration behavior.
- Work on the current `develop` checkout; the repository says feature branches
  are preferred rather than required, and the user explicitly requested this checkout.
- TDD mode: disabled by `docs/AI_CONTEXT.md`; use focused functional tests.
- Test runner: `npm test -- --watch=false --include=src/services/colaboration/p2p.service.spec.ts` from `front_generador_bd`.
- Delivery strategy: `ask-on-risk`; forecast is under 250 authored changed lines,
  so no chain strategy is expected.
- Commit evidence will remain intentionally absent because the user prohibited commits.

## Tasks

- [x] **ICE-1 — Buffer and flush early ICE candidates with focused tests**
  - Acceptance: early candidates are queued without immediate application.
  - Acceptance: offer and answer paths flush queued candidates in arrival order.
  - Acceptance: ready peers apply new candidates immediately.
  - Acceptance: flushed candidates are not applied twice and reset clears pending state.
  - Checks: focused P2P spec, then frontend suite/build if reasonably cheap.
  - Evidence: focused spec `6/6` passed; TypeScript spec compilation passed;
    production build passed with existing budget/CommonJS warnings; full suite
    reached `20/24` with four unrelated existing component-test failures
    (`NG0908` missing Zone.js in three specs and one stale app-title assertion).
  - Review/delivery: RDD/GGA not run; no commit created by explicit user instruction.

## Progress and next step

ICE-1 is implemented and verified in the working tree. The focused behavior and
build pass; the unrelated pre-existing full-suite failures are recorded above.
Next: user review of the uncommitted diff; no push or GGA was performed.
