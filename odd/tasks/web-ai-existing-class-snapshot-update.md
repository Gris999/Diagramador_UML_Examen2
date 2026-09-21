# Fix AI full-snapshot updates for existing UML classes

## Objective

Apply incoming AI full-snapshot class content to the existing JointJS class
without changing its identity, duplicating it, or losing its layout.

## Problem and why

`DiagramService.loadFromJson` reuses a matching class when the text/voice AI
flow passes `isStorageLoad=true`, but that branch restores only position and
size. Updated names, attributes, and methods are silently discarded.

## Authorized scope

- Match an existing class by stable ID, with the current name match as fallback.
- Reuse the existing JointJS model and apply incoming supported class content.
- Preserve position and size unless the incoming snapshot provides them.
- Add focused DiagramService regression coverage for update, identity, layout,
  storage restoration, and normal creation behavior.

Excluded: AI prompt/backend/provider changes, collaboration behavior, XMI,
Flutter, unrelated DiagramService refactors, Docker/databases, commits, and
pushes. GGA runs only against the final staged patch.

## Constraints and decisions

- Sole writer on `develop` at
  `d6d5d4ca8c06b757fd1909e29250eea7621758fb`.
- Keep the fix localized to the existing full-snapshot reuse branch.
- TDD mode is disabled by `docs/AI_CONTEXT.md`; use focused regression tests.
- Focused runner: `npm test -- --watch=false --include=src/services/diagram/diagram.service.spec.ts`
  from `front_generador_bd`.
- Type check: `npx tsc --noEmit -p tsconfig.spec.json` from `front_generador_bd`.
- Delivery strategy: `ask-on-risk`; forecast is under 200 authored changed lines.
- Rollback boundary: remove the existing-class content assignment in
  `diagram.service.ts`, the focused regression cases/fake-model additions in
  `diagram.service.spec.ts`, the text-AI status update in `docs/GAP_MATRIX.md`,
  and this task document.

## Tasks

- [x] **AI-SNAPSHOT-1 — Update existing class content without duplication**
  - Acceptance: an ID/name-matched class retains identity and layout while
    applying incoming name, attributes, and methods; new classes still create.
  - Checks: focused DiagramService regression tests.
  - Evidence: the focused DiagramService suite passed 15/15, including the
    three-attribute `Producto` snapshot, method replacement, unchanged implicit
    layout, stable identity, no duplicate, and existing new-class coverage.

- [x] **AI-SNAPSHOT-2 — Verify storage and build compatibility**
  - Acceptance: explicit stored position/size/content restore correctly, type
    checking passes, and the final diff contains no unrelated changes.
  - Checks: focused tests, spec TypeScript check, production build if needed,
    `git diff --check`, and final diff/status inspection.
  - Evidence: explicit position, size, name, attribute, and method restoration
    passed on the reused class; spec TypeScript compilation and the production
    build passed. The build retained the existing bundle-budget and CommonJS
    warnings. Final diff verification found only the localized service change,
    focused spec updates, GAP Matrix evidence, and this task document.
  - Runtime/review evidence: independent read-only review passed with no
    blocking defects. A fresh real Google Gemini replay created `Producto`,
    added `precio:decimal`, then added `calcularTotal():decimal` on the same
    JointJS class while retaining prior content, position `{x:100,y:100}`, and
    a single class instance; no new console, relationship, collaboration, or
    XMI regression was observed.

## Progress and next step

Both tasks are implemented and verified by focused automation, independent
review, and a real Google Gemini create/attribute-edit/method-edit replay. The
sandboxed Karma/build processes exited 134 before completing, while the required
out-of-sandbox reruns passed; these were environment reruns, not implementation
repair attempts. No commit, push, Docker, or database action was performed;
staging and GGA are handled by the final review gate.
