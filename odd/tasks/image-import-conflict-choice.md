# Add safe choices for non-empty image import

## Objective

Prevent Image → UML results from silently mixing with a non-empty diagram by
offering Replace, Merge, and Cancel without changing image recognition or the
active collaboration room.

## Problem and why

The image upload flow applies valid generated UML immediately through
`DiagramService.loadFromJson`, so importing into an existing diagram appends
overlapping classes and relationships without user consent.

## Authorized scope

- Preserve immediate image import for an empty diagram.
- Hold a valid generated result when the current graph has UML elements.
- Show a small Angular-native three-action dialog for Replace, Merge, or Cancel.
- Replace through existing per-cell local removal so collaboration receives the
  same delete operations as normal editor deletion before imported additions.
- Add focused SidePanel and DiagramService regression coverage.

Excluded: image recognition/provider/backend behavior, XMI import, AI prompts,
collaboration rooms/roles/Redis/WebRTC, relationship presentation, auto-size,
PNG export, participants UI, Flutter, Docker/databases, authentication,
dependencies, staging, commits, pushes, and GGA.

## Constraints and decisions

- Sole writer on `develop` at
  `3d3e9c26bce185a4c50e4943989253806b82e09e`.
- `DiagramService` already broadcasts `{t:'delete', id}` from its graph `remove`
  handler for local removals; remote deletion marks `{collab:true}` to prevent
  loops. Replace will therefore remove a snapshot of links first and elements
  second via each cell's existing `remove()` method, then load the image UML.
- Do not use `graph.clear()`, reload, leave the room, or touch presence state.
- TDD mode is disabled by `docs/AI_CONTEXT.md`; use focused regression tests.
- Focused runner: `npm test -- --watch=false --browsers=ChromeHeadless
  --include=src/app/side-panel/side-panel.spec.ts
  --include=src/services/diagram/diagram.service.spec.ts` from
  `front_generador_bd`.
- Type check: `npx tsc --noEmit -p tsconfig.spec.json` from `front_generador_bd`.
- Build: `npm run build` from `front_generador_bd`.
- Delivery strategy: `ask-on-risk`; the final work unit is about 460 authored
  changed lines including focused tests and this recovery document. No chain
  decision is needed yet because no commit is authorized in this work unit.
- Rollback boundary: remove the focused changes in `side-panel.ts`,
  `side-panel.html`, `side-panel.spec.ts`, `diagram.service.ts`,
  `diagram.service.spec.ts`, and this task document.

## Tasks

- [x] **IMAGE-CHOICE-1 — Add collaboration-safe replacement primitives**
  - Acceptance: DiagramService can report whether UML elements exist and replace
    by removing existing cells through the normal collaborative removal path
    before loading generated UML; no room or transport state changes.
  - Checks: focused DiagramService specs.
  - Evidence: DiagramService coverage verifies non-empty detection, link-first
    and element-second `cell.remove()` ordering, no `graph.clear()`, generated
    UML loading only after removals, and cleared selection. Existing graph
    removal events provide the collaboration delete broadcasts.

- [x] **IMAGE-CHOICE-2 — Gate image results behind a three-choice dialog**
  - Acceptance: empty diagrams import immediately; non-empty diagrams retain a
    single pending result and apply nothing before Replace or Merge; Cancel drops
    it; every action closes the dialog and leaves no stale result.
  - Checks: focused SidePanel specs.
  - Evidence: tests verify immediate empty import, deferred non-empty import,
    Replace-only generated content, Merge preservation, Cancel preservation, and
    that repeated decisions cannot reuse consumed/cancelled pending data.

- [x] **IMAGE-CHOICE-3 — Render the bounded Angular-native modal**
  - Acceptance: centered light dialog uses the required Spanish title/message
    and visually distinct Replace, Merge, and Cancel buttons; Escape cancels.
  - Checks: focused SidePanel DOM specs and production build.
  - Evidence: the rendered dialog contains the required Spanish title/message,
    destructive red Replace, primary cyan Merge, neutral Cancel, and a document
    Escape handler; DOM interaction tests exercise every action.

- [x] **IMAGE-CHOICE-4 — Verify scope and existing error handling**
  - Acceptance: upload/provider invalid/error paths keep their existing behavior;
    focused tests, TypeScript, build, diff check, and final paths pass without
    unrelated changes.
  - Checks: commands recorded above plus `git diff --check` and `git status`.
  - Evidence: focused ChromeHeadless specs passed 28/28, including invalid-result
    and provider-error paths; spec TypeScript compilation passed; production
    build passed with the existing bundle-budget/CommonJS warnings; diff check
    passed. Sandboxed test/build startup exited 134, while the authorized
    out-of-sandbox reruns passed. No implementation repair was required.

## Progress and next step

All four tasks are implemented and verified. The final scope contains the two
SidePanel implementation files, its focused spec, the DiagramService helper and
focused spec, plus this recovery document. No staging, commit, push, GGA, AI,
XMI, collaboration-semantic, Docker, or database action was performed.
