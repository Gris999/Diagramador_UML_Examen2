# Add generated Flutter local-LLM command extraction

## Objective

Generate an optional, genuine on-device GGUF command extractor for every
Flutter project while preserving the deterministic parser, existing validator,
router, service adapters, SQLite fallback, and two-phase delete safety.

## Problem and why

Generated apps currently interpret text and transcribed voice only through a
deterministic schema-aware parser. RF-22 requires a genuine local model path,
but generated apps have no model import, runtime lifecycle, structured local
inference, or safe fallback integration.

## Authorized scope

- Add stable `llamadart` GGUF inference and its matching Apple companion to the
  generated pubspec.
- Add local `.gguf` selection, app-controlled copying, persisted metadata, and
  load/unload state without model bundling or automatic model downloads.
- Generate schema-grounded strict JSON extraction and map valid output to
  `BusinessCommand`.
- Reuse `CommandValidator`, `CommandRouter`, `EntityServiceAdapter`, and the
  existing two-phase delete confirmation.
- Preserve deterministic `CommandParser` fallback for every local-model failure.
- Add compact model state controls and an accurate local-AI source indicator.
- Generate and verify a project-owned iOS 16.4 setup tool after `flutter create`.
- Update focused generator/generated-app tests and native setup documentation.

Excluded: Whisper, wake words, Siri/App Intents, background listening,
navigation commands, automatic model downloads, cloud/Gemini mobile fallback,
web Gemini, XMI, collaboration, Redis/WebRTC, Spring/Postman generation, AWS,
and GAP_MATRIX.md.

## Constraints and decisions

- Runtime pair: `llamadart` 0.8.23 and
  `llamadart_llama_cpp_flutter` 0.0.18.
- Generated SDK constraints remain Dart `>=3.12.0 <4.0.0`; add the compatible
  Flutter `>=3.38.0` floor and require iOS 16.4+ for local AI.
- Use maintained Flutter packages `file_selector` 1.1.0 and
  `path_provider` 2.1.6 for user-selected files and app-owned storage.
- The acceptance model is Qwen2.5-0.5B-Instruct GGUF with a Q4-class
  quantization, but no model file or download URL is generated.
- The model only proposes structured JSON. Validation and execution remain in
  the existing deterministic business pipeline.
- Strict TDD is disabled by `docs/AI_CONTEXT.md`; use focused regression tests.
- Focused runner:
  `back_generador_bd/.venv/bin/python back_generador_bd/manage.py test uml_api.tests.test_flutter_generator`.
- Generated app checks: `flutter pub get`, `flutter analyze`, `flutter test`,
  `flutter build apk`, and `flutter build ios --no-codesign`.
- Delivery strategy: `ask-on-risk`. Forecast is above 400 authored lines because
  generator templates, generated Dart tests, documentation, and recovery
  evidence must ship together. No chain decision is needed until a commit or PR
  is authorized.
- Rollback boundary: revert the local-LLM generator methods/wiring,
  `test_flutter_generator.py` coverage, setup documentation, and this task file.

## Tasks

- [x] **LOCAL-LLM-A1 — Enforce generated-project compatibility**
  - Acceptance: generated pubspec resolves the selected stable packages and a
    project-owned setup tool applies/verifies iOS deployment target 16.4 after
    platform scaffolding without modifying Flutter SDK templates.
  - Checks: generator tests plus execution against a fresh scaffold.
  - Evidence: `_generate_pubspec` now emits `llamadart: ^0.8.23`,
    `llamadart_llama_cpp_flutter: ^0.0.18`, `file_selector: ^1.1.0`,
    `path_provider: ^2.1.6`, and a `flutter: '>=3.38.0'` environment floor
    alongside the existing Dart floor; `flutter pub get` resolved all of them
    cleanly (`llamadart 0.8.24`, `llamadart_llama_cpp_flutter 0.0.19` via
    caret constraints). New `_generate_ios_local_ai_setup_script` emits
    `tool/configure_ios_local_ai.sh` (POSIX sed/grep only). Empirically
    discovered and handled: current Flutter (3.47.2) integrates iOS plugins
    via Swift Package Manager by default and does **not** generate
    `ios/Podfile` at all — the script requires only `project.pbxproj` and
    treats `Podfile` as optional/best-effort, verified against a real
    `flutter create . --platforms=ios,android,web` scaffold. `./tool/configure_ios_local_ai.sh`
    then `--verify` both passed; `flutter build ios --no-codesign` failed
    before the fix (Xcode: "requires minimum platform version 16.4 ... but
    this target supports 15.0") and succeeded after it.

- [x] **LOCAL-LLM-A2 — Generate model management and structured extraction**
  - Acceptance: a selected `.gguf` is copied to app-controlled storage,
    remembered, loaded/unloaded safely, and used only to return schema-grounded
    strict command JSON mapped defensively to `BusinessCommand`.
  - Checks: generated unit tests with fake storage/inference backends.
  - Evidence: `lib/assistant/local_model_manager.dart` (file_selector pick →
    copy into `path_provider` app-support dir → `LlamaEngine.loadModel` →
    `LocalModelState` notifier; auto-loads a previously-imported model on
    startup; zero network calls). `lib/assistant/local_llm_command_extractor.dart`
    builds its prompt purely from `AppSchema.entities` at Dart runtime (no
    project-specific literal anywhere in the generator's Python or emitted
    Dart), uses `llamadart`'s real `createStructuredJson`/`LlamaStructuredOutput.jsonObject`
    grammar-constrained JSON path, has a bounded timeout, defensively
    extracts JSON from markdown-fenced/prose-wrapped output, shape-validates
    before constructing a `BusinessCommand`, and exposes an injectable
    `rawInferenceOverride` seam used by every generated test (no `.gguf`
    required). Verified real `llamadart` API shapes directly against the
    cached package sources (`~/.pub-cache`) rather than assuming them.

- [x] **LOCAL-LLM-A3 — Integrate fallback, UI, and delete safety**
  - Acceptance: valid local inference uses the existing validator/router;
    every missing/error/timeout/malformed/schema-invalid case falls back to the
    deterministic parser; DELETE still creates `PendingDelete` and mutates only
    after explicit confirmation; UI shows compact model state and labels only
    successful local inference.
  - Checks: generated extractor/interpreter/router/widget regression tests.
  - Evidence: `_submit()` in `assistant_view.dart` tries the LLM extractor
    only when `LocalModelManager.state == ready`; any failure falls through
    to the unchanged `CommandParser.parse(text)` call. `CommandValidator`,
    `CommandRouter`, `EntityServiceAdapter`, and the two-phase DELETE
    confirmation dialog were not modified at all. New compact
    `_buildLocalAiStatus()` row (Not configured / Loading / Ready / Unavailable
    states, each with a select/change-model action). Result history entries
    carry a `usedLocalAi` flag set true only on genuine LLM-extraction
    success; the fallback path never sets it. One safety fix made during
    implementation: the error-state label was changed from an
    exception-message-interpolated string to a fixed "Local AI: Unavailable"
    to eliminate any risk of colliding with existing widget tests'
    case-sensitive `find.textContaining('error')` assertions.

- [x] **LOCAL-LLM-A4 — Verify a fresh generated application and document truth**
  - Acceptance: focused generator tests, generated Flutter analysis/tests,
    Android/iOS builds, target verification, and diff checks pass; setup docs
    describe model import, local inference, fallback, and unvalidated physical
    acceptance without claiming Whisper/wake-word/local voice work.
  - Checks: commands listed above plus `git diff --check` and final path audit.
  - Evidence: `back_generador_bd/.venv/bin/python back_generador_bd/manage.py test uml_api.tests.test_flutter_generator`
    — 29/29 passed (24 pre-existing unchanged + 5 new, including a
    byte-identical-across-two-unrelated-schemas proof that nothing is
    hardcoded). Fresh generated project: `flutter pub get` OK, `flutter
    analyze` 0 issues, `flutter test` 50/50 passed (14 new local-LLM
    extractor cases: create/read/update/delete JSON, markdown-fenced JSON,
    malformed JSON, thrown exception, timeout, no-model regression, unknown
    action, unknown entity, unknown field, DELETE-via-LLM still two-phase —
    all against fake backends, no `.gguf` required), `flutter build apk`
    succeeded, `flutter build ios --no-codesign` succeeded after the iOS
    setup script, `flutter build web` succeeded. `git diff --check` clean.
    `docs/FLUTTER_ASSISTANT_SETUP.md` updated with an honest "what is and
    isn't verified" split — explicitly does not claim physical Qwen
    inference, RF-22 DONE, Whisper, wake word, or Siri/App Intents.

- [ ] **LOCAL-LLM-A5 — Fail closed on unreliable mutating extraction and complete physical READ acceptance**
  - Acceptance: action-aware normalization rejects an LLM-proposed mutation
    unless the raw request contains a recognized matching mutating intent;
    CREATE removes only an auto-increment PK, requires every required field,
    and rejects ungrounded numeric values; READ discards `data` and keeps only
    non-empty schema filters; deterministic fallback turns a supported Spanish
    read request into READ, while an ambiguous/typo request cannot produce a
    mutation. READ output shows compact dynamic row data.
  - Checks: focused Python generator tests; a fresh project generated from
    `REPRESENTATIVE_UML`; full `flutter test`; `flutter analyze`; diff check;
    rebuilt signed physical iPhone app; then only the bounded correct-read and
    typo/ambiguous physical scenarios.
  - Current evidence: real Qwen2.5-0.5B-Instruct Q4_K_M loaded successfully on
    an iPhone 12 and physical CREATE passed. The first physical READ replay,
    `Busca Coca-cola`, failed safely with `No conozco la entidad
    "Coca-cola".`: the current local-LLM prompt does not explicitly separate
    schema entity names from record field values, and the deterministic
    fallback consequently interprets the first token after `Busca` as an
    entity. A5 is reopened for a schema-dynamic extractor-only correction;
    CRUD execution remains out of scope until the new extraction regression
    passes. The generator now fails closed
    when an LLM proposes a mutation that disagrees with the recognized raw-text
    action, rejects unknown entities, strips only auto-increment CREATE PKs,
    requires complete CREATE data, rejects ungrounded numeric values using
    whole-number comparisons, cleans READ filters, and discards READ data.
    Focused Python generator tests pass 30/30. A fresh project generated from
    the broad `REPRESENTATIVE_UML` fixture passes all 62 Dart tests and
    `flutter analyze` with zero issues. The exact Producto/Categoria physical
    schema was regenerated from the fixed generator; all 53 Dart tests pass.
    Its scaffold lints have 41 pre-existing informational findings, so the
    strict analyze command exits nonzero while `flutter analyze
    --no-fatal-infos` passes with no errors or warnings. Temporary diagnostic
    prints and the obsolete one-off PK helper are absent. Only the physical
    READ/typo replay remains: the app was uninstalled to clear its contaminated
    data, rebuilt, signed, installed, launched on the iPhone 12, and has logs
    attached. The next bounded check is generated-Dart coverage proving that a
    READ keeps the canonical schema entity in `entity` and places the requested
    record value under that entity's generated `nameField`, while invalid
    entity output still fails into the unchanged deterministic fallback. That
    extractor correction is now implemented: the runtime prompt enumerates
    schema-derived READ shapes and explicitly separates entity types from
    record values, while decoded aliases are resolved and canonicalized through
    `AppSchema.resolveEntity`; unknown values emitted as entities still fail
    closed. The new tests were observed RED before the change, then the focused
    generated extractor suite passed 22/22, the Python generator suite passed
    31/31, representative `flutter analyze` reported no issues, and
    `git diff --check` passed. The fixed extractor and its physical-schema
    tests were regenerated into the external iPhone harness; its focused
    extractor suite passed 22/22 and analyze passed with only the 41 known
    informational lints. The rebuilt app is running with logs attached and
    persisted-model autoload reached `LocalModelState.ready`; only the bounded
    `Busca Coca-cola` replay remains pending.

- [ ] **LOCAL-LLM-A6 — Bound local-model lifecycle and add one CPU fallback**
  - Acceptance: model loads are serialized; every failed candidate engine is
    disposed; an owned manager is disposed with `AssistantView`; a failed
    primary load performs exactly one CPU-only fallback without re-importing a
    persisted GGUF; fallback success ends ready and double failure ends error.
  - Checks: focused generator suite; representative and physical-schema
    generated Dart tests/analyze; `git diff --check`; rebuilt signed iPhone app
    with persisted-model autoload and logs attached.
  - Current evidence: the cold primary worker initialization timed out after
    30 seconds while Metal initialization was still running. A later CPU load
    of the same persisted 491400032-byte GGUF used 0/25 GPU layers, created the
    context, and reached ready in 259 ms. Implementation and automated checks
    are pending.

## Progress and next step

LOCAL-LLM-A1 through A4 remain implemented. Physical iPhone work is active
under LOCAL-LLM-A5: model import/load and CREATE are proven, but the first READ
replay exposed an entity-versus-field-value extraction gap. The immediate next
step is to repeat only the bounded `Busca Coca-cola` READ replay in the running
physical build. UPDATE/DELETE/fallback/airplane-mode acceptance has not started.
RF-22 remains incomplete. No commit, stage, push, or GGA action is authorized.
