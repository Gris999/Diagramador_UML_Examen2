# Fix UML editor presentation regressions

## Objective

Correct four confirmed presentation defects in UML image export, relationship
routing, class content sizing, and the participants panel without changing
diagram semantics, collaboration authority, or AI behavior.

## Problem and why

PNG export leaves the raster canvas transparent, relationships use default
straight routing, long class content can escape the class rectangle, and the
participants panel is visually larger than its toolbar role requires.

## Authorized scope

- Fill exported PNG canvases with the editor's light background before drawing.
- Configure every existing relationship-construction path with Manhattan routing
  and a rounded connector.
- Grow UML class width only when rendered name, attribute, or method text needs it,
  while preserving height resizing, minimum/current width, and position.
- Compact the existing participants panel and bound long lists with scrolling.
- Add focused regression coverage for all four presentation fixes.

Excluded: import confirmation/merge behavior, AI/Gemini/backend behavior,
collaboration semantics or roles, Redis/WebRTC/XMI/Flutter, Docker/databases,
authentication, dependencies, staging, commits, pushes, and GGA.

## Constraints and decisions

- Sole writer on `develop` at
  `2b8d8afa56da30e7de60412730f592ef7f3ae0a9`.
- Reuse JointJS `manhattan` and `rounded`; add no layout dependency.
- Preserve the existing 180px class minimum and never shrink the current width.
- Measure rendered SVG text where available; do not introduce a giant fixed width.
- TDD mode is disabled by `docs/AI_CONTEXT.md`; use focused regression tests.
- Focused runner: `npm test -- --watch=false --browsers=ChromeHeadless
  --include=src/services/diagram/diagram.service.spec.ts
  --include=src/services/diagram/edition.service.spec.ts
  --include=src/app/participants-panel/participants-panel.spec.ts` from
  `front_generador_bd`.
- Type check: `npx tsc --noEmit -p tsconfig.spec.json` from `front_generador_bd`.
- Build: `npm run build` from `front_generador_bd`.
- Delivery strategy: `ask-on-risk`; forecast is about 320 authored changed lines.
  No commit is authorized in this work unit.
- Rollback boundary: remove the focused changes in `diagram.service.ts`,
  `edition.service.ts`, `participants-panel.html`, their three focused spec files,
  and this task document.

## Tasks

- [x] **PRESENTATION-1 — Make PNG export background explicit**
  - Acceptance: raster export fills `#f8f9fa` before drawing the SVG; diagram
    content remains the only exported application content.
  - Checks: focused DiagramService spec.
  - Evidence: the export drawing helper test verifies `#f8f9fa` is applied and
    `fillRect` runs before `drawImage`; export still serializes only `paper.svg`.

- [x] **PRESENTATION-2 — Route all relationship types readably**
  - Acceptance: association, generalization, aggregation, composition, and
    dependency links use Manhattan routing and a rounded connector across local,
    imported, and remote construction paths.
  - Checks: focused DiagramService specs.
  - Evidence: association, generalization, aggregation, composition, and
    dependency retain their existing marker attributes while all typed, default,
    and remote builders expose `manhattan`/`rounded`.

- [x] **PRESENTATION-3 — Grow UML classes for overflowing text**
  - Acceptance: short classes retain normal width; long methods/attributes grow
    width; textWrap follows the resulting width; height behavior and position
    remain unchanged.
  - Checks: focused EditionService specs.
  - Evidence: new tests verify 180px short content, method growth to 280px,
    attribute growth to 260px, no shrink from 320px, synchronized textWrap, and
    unchanged position.

- [x] **PRESENTATION-4 — Compact and bound the participants panel**
  - Acceptance: header shows `Participantes (N)`; current-user and role labels
    remain; host-only removal is preserved; many rows stay within a scrollable
    maximum height.
  - Checks: focused ParticipantsPanel specs.
  - Evidence: component tests verify `Participantes (N)`, `(Tú)`, host-only
    removal, promotion, 12 rendered rows, `max-h-48`, and `overflow-y-auto`.

- [x] **PRESENTATION-5 — Verify the bounded work unit**
  - Acceptance: focused specs, TypeScript check, production build, diff check,
    and final path inspection pass without unrelated changes.
  - Checks: commands recorded above plus `git diff --check` and `git status`.
  - Evidence: focused ChromeHeadless selection passed 25/25; spec TypeScript
    compilation passed; production build passed with only the existing bundle
    budget and CommonJS warnings; `git diff --check` passed. The sandboxed test
    and build processes exited 134 during startup, while their authorized
    out-of-sandbox reruns passed. No implementation repair attempt was needed.

## Progress and next step

All five tasks are implemented and verified. Final scope contains the three
authorized presentation implementation files, three focused spec files, and
this recovery document; no staging, commit, push, GGA, Docker, database, AI,
import, or collaboration-semantic action was performed.
