# Flutter Assistant — Native Setup Notes

The Flutter generator (`back_generador_bd/uml_api/services/flutter_generator.py`)
only emits `lib/`, `test/` and `pubspec.yaml`. It does **not** emit `ios/`,
`android/` or `web/` platform runners — that architecture is unchanged by the
assistant feature. After downloading a generated project, scaffold the
missing platform folders yourself:

```bash
cd generated_flutter_app
flutter create . --platforms=ios,android,web
flutter pub get
```

`flutter create .` will not overwrite `lib/`, `test/` or `pubspec.yaml`; it
only fills in the platform runner folders next to them.

Generated projects now require **Dart SDK >= 3.12.0** (the pubspec
environment floor was raised from `>=3.0.0`), because `speech_to_text` is
pinned to `^7.5.0`, which itself requires Dart `^3.12.0`. Use a Flutter SDK
that bundles Dart 3.12 or newer (Flutter 3.44+).

Generated projects also require **Flutter SDK >= 3.38.0** and **iOS 16.4+**
for the new local-LLM command extraction feature (see below) — the pubspec
`environment:` block now declares both floors explicitly.

## Local on-device LLM command extraction (new)

Generated apps now include a genuine local LLM command-extraction path,
built on the `llamadart` + `llamadart_llama_cpp_flutter` runtime
(`lib/assistant/local_model_manager.dart`,
`lib/assistant/local_llm_command_extractor.dart`). This runs a real GGUF
model on-device to turn typed or transcribed text into a structured
`BusinessCommand`, which then flows through the **exact same, unmodified**
`CommandValidator` → `CommandRouter` pipeline as the deterministic parser —
including the same two-phase DELETE confirmation. The model never executes
anything itself; it only ever proposes a command.

**No model is bundled with the app, and none is downloaded on its own.**
The person gets one in the assistant view, in either of two ways, both an
explicit action: **"Descargar IA local"** (asks for confirmation first —
about 1.1 GB, better on Wi-Fi — and downloads Qwen2.5-1.5B-Instruct Q4_K_M,
Apache-2.0, 1,117,320,736 bytes, from Hugging Face with a progress indicator
and a "Cancelar" button; `lib/assistant/model_downloader.dart` writes
`<file>.part` and renames it at the end, so a cut connection never leaves a
half model, and it refuses anything too small to be a model), or **"Elegir
modelo"** (imports a compatible `.gguf` through `file_selector`). Either way
the file is kept in the app's own `path_provider` support directory so it
persists across restarts (an install over the top keeps it; uninstalling the
app deletes it), and after that the assistant works without internet.
Versions up to 2026-11-07 (afternoon) used Qwen2.5-0.5B (0.5 GB), which was
enough to interpret orders but not to hold a conversation; whoever still has
that file sees **"Descargar IA mejorada"** next to the status, and a failed
download keeps the model that already works. The extractor and the chat are
not tied to any specific model — any compatible GGUF chat model can be used.

### Two ways of answering (since 2026-11-07, night)

With the model ready, every message takes one of two paths. The model is the
same one in both; what changes is how much it is trusted.

1. **Orders on the data** (the message starts with a data verb: crea, agrega,
   elimina, borra, cambia, actualiza, muestra, lista, dame, ver...). Politeness
   and fillers are removed first (`AssistantTexts.orderText`: "por favor, lista
   todos los X" → "lista los X", "crea un X llamado Ana" → "crea un X Ana").
   The model proposes a structured command (grammar-constrained JSON) and the
   extractor distrusts it: it only keeps fields of the real schema, drops a
   value the person never said (copied from the prompt or invented), drops
   template placeholders, accepts numbers sent as text, repairs fields the
   model put in the wrong object, and a mutation must start with a verb the
   rules recognise. Then the unchanged validator → router → two-phase DELETE.
   If the model fails, the deterministic rules take over
   (`CommandParser`, which also understands "con id 3" / "número 3").
2. **Conversation** (anything else: greetings, questions, concepts of
   management systems). `lib/assistant/local_llm_chat.dart` asks the model for
   free text with a system prompt built at run time from `AppSchema`: app name,
   entities and fields, what it can do and what it cannot (no internet search,
   no e-mail), a rule to answer "how do I…?" with the exact order to type
   instead of inventing menus, and — when the question names an entity — the
   real data (how many records, how they are called). Short memory, 40 s
   timeout; any failure falls back to the fixed texts. "Ayuda" keeps its exact
   text. If neither path understands a message, the model answers instead of
   "No logré entender eso".

Without a model nothing changes: fixed texts for greetings/help and the rules
for orders. Every assistant bubble carries a tag so it can be checked at a
glance: **«IA local»** (written by the model, or a command the model
interpreted) or **«Respuesta de la app»** (fixed text or the rules). A fallback
is never labelled as AI, regardless of why the fallback happened.

### How to check that it is a real AI (measured on 2026-11-07)

Measured on a Mac (CPU, the real `llamadart` engine) with Qwen2.5-1.5B-Instruct
Q4_K_M and a generated app with `Empleado(nombre)` and `Departamento(titulo)`;
each AI answer took 0.7 to 2.4 s. The same phrases were also run through the
deterministic rules, so the difference is visible:

| Phrase | Rules only | With the model |
|---|---|---|
| "cambia el nombre del empleado 2 a Marta" | update with a wrong filter (`nombre: "del empleado 2"`) | update of id 2 → `nombre: Marta` |
| "actualiza el departamento 1 a titulo Finanzas" | wrong filter (`titulo: 1`) | update of id 1 → `titulo: Finanzas` |
| "crea un departamento llamado Ventas" | `titulo: Ventas` | `titulo: Ventas` |
| "borra al empleado número 3" | delete of id 3 | delete of id 3 |
| "¿cuántos empleados hay?" (3 loaded) | not an order | "Hay 3 empleados: Ana, Luis y Marta." (from the real data) |
| "¿qué más puedes hacer?" | exact help text | answers within its real limits |
| "¿puedes enviarle un correo a Ana?" | not an order | says it cannot act outside the app |

Ways to see it with your own eyes: (1) the tag «IA local» over the bubble;
(2) turn on airplane mode and keep talking — nothing leaves the phone; (3) ask
something the fixed texts cannot know, such as a count taken from the data or
a concept of management systems; (4) ask the same thing twice: the wording
changes, fixed texts never do.

Honest limits, found while measuring: it is a small model (1.5 billion
parameters). Its explanations of concepts can be imprecise (it defined "asiento
contable" loosely), it can word things differently from one run to the next, and
creating a record whose entity has a *required* relation (for example an
employee that must belong to a department) is not completed by the model — the
rules take it and the validator asks for the missing data. Orders are protected
from these errors by the guards above; conversation is not, which is why the
prompt tells it to use only the real data and to admit what it cannot do. Speed
on a physical iPhone was not measured yet.

### iOS 16.4+ setup

Because the local-LLM native runtime requires iOS 16.4+, run the generated
`tool/configure_ios_local_ai.sh` script once after scaffolding the iOS
platform folder:

```bash
flutter create . --platforms=ios,android,web
tool/configure_ios_local_ai.sh            # applies the 16.4 deployment target
tool/configure_ios_local_ai.sh --verify   # verifies it, without modifying anything
```

The script only touches `ios/Runner.xcodeproj/project.pbxproj` (always),
`ios/Podfile` (only if present) and `ios/Runner/Info.plist` (it adds the two
voice-permission texts, once; see below) inside the generated project — it
never touches Flutter SDK files. Note: with Flutter's current default Swift
Package Manager integration, `flutter create` does not generate a
`ios/Podfile` at all; the script detects this and only updates
`project.pbxproj` in that case, which is what Xcode actually requires to
resolve the `llamadart_llama_cpp_flutter` Swift package.

## Required native permissions for voice input

The assistant's voice input (`lib/assistant/voice_input_controller.dart`)
uses `package:speech_to_text`, which needs microphone and speech-recognition
permission strings that only exist inside the platform runner folders the
generator does not produce. Add them by hand after `flutter create .`:

### iOS — `ios/Runner/Info.plist`

**`tool/configure_ios_local_ai.sh` already adds these two keys** (and
`--verify` fails if they are missing). Only add them by hand if you did not
run the script. They are **mandatory**: without them iOS **closes the app**
(`TCC … PRIVACY_VIOLATION`) as soon as the assistant asks for the microphone or
speech recognition. Keys, inside the top-level `<dict>`:

```xml
<key>NSMicrophoneUsageDescription</key>
<string>Esta app usa el micrófono para el asistente por voz.</string>
<key>NSSpeechRecognitionUsageDescription</key>
<string>Esta app usa reconocimiento de voz para interpretar comandos del asistente.</string>
```

### Android — `android/app/src/main/AndroidManifest.xml`

Add these permissions as direct children of `<manifest>`:

```xml
<uses-permission android:name="android.permission.RECORD_AUDIO"/>
<uses-permission android:name="android.permission.INTERNET"/>
```

And, inside the existing `<queries>` block (Android 11+ / API 30+ package
visibility requirement for `speech_to_text` to find an installed
speech-recognition service on the device):

```xml
<intent>
    <action android:name="android.speech.RecognitionService"/>
</intent>
```

On **Android**, without these the OS denies microphone/speech access and
`VoiceInputController.initialize()` reports voice input as unavailable — the
mic button stays hidden and the typed assistant keeps working normally. On
**iOS** it is not silent: the app is closed by the system (see above), so
the Info.plist texts are not optional.

## What is and isn't verified

- Verified by build: `flutter analyze`, `flutter test`, `flutter build web`,
  `flutter build apk`, and `flutter build ios --no-codesign` all succeed with
  `speech_to_text: ^7.5.0`, `llamadart`, `llamadart_llama_cpp_flutter`,
  `file_selector`, and `path_provider` present, these permissions applied,
  and the iOS deployment target raised to 16.4 via the setup script.
- **Physically validated on iPhone 12**: the generated application runs; CRUD,
  offline SQLite persistence, and the deterministic schema-aware text CRUD
  assistant work; voice input works in airplane/offline conditions; and voice
  UPDATE plus two-phase DELETE passed.
- Local-LLM command extraction (`lib/assistant/local_model_manager.dart`,
  `lib/assistant/local_llm_command_extractor.dart`) is implemented and
  covered by focused generated tests using fake inference/storage backends
  (no `.gguf` file required for any automated test) — this proves the
  extraction, JSON-parsing, schema-grounding, fallback, and two-phase-DELETE
  behavior in isolation. **Physical on-device inference with a real Qwen (or
  any other) GGUF model has NOT been validated yet** — that is explicitly
  out of scope for this work unit and remains a next step before this
  capability can be considered proven end-to-end on a physical device.
- **2026-11-07, real model, no phone involved.** With the real
  `qwen2.5-0.5b-instruct-q4_k_m.gguf` (Q4_K_M, 491 MB) and the real
  `llamadart` runtime: (a) on macOS (pure Dart, the app's own
  `LocalLlmCommandExtractor`) the model loads in ~1.2 s and answers in
  0.6–2.3 s; 3 of 6 Spanish phrases became a valid command (list, delete,
  create a department), the others were rejected by the validator by design
  (a required relation is missing, wrong JSON shape, small talk) and fall
  back to the deterministic parser; output is not deterministic between
  runs. (b) In the **iOS simulator** (iPhone 17 Pro), the real app shows
  "Local AI: Ready — qwen2.5-0.5b…" and, **with the model on CPU**
  (`ModelParams(gpuLayers: 0)`), "lista todos los empleados" produced
  "IA local: 2 resultado(s)" from the local SQLite database in ~4.9 s, offline.
  With the default (all layers on the GPU) the simulator's emulated Metal
  returned `{}`, so the app silently used the deterministic parser: that is a
  simulator artifact (the same model works on the Mac), **not yet checked on a
  physical iPhone**. Physical-device inference is still the pending step.
- The generated `pubspec.yaml` now pins `llamadart: 0.8.24` and
  `llamadart_llama_cpp_flutter: 0.0.19` (they share native runtime v0.4.1).
  With the previous caret ranges `pub` resolved `0.8.24 + 0.0.23` on
  2026-11-07, a pair `llamadart` rejects on Apple ("does not uniquely pin the
  required native runtime"), so freshly generated projects did not build for
  iOS/macOS. The older pair `0.8.23 + 0.0.18` does not work either with the
  current Flutter (its build hook fails on a missing `Artifacts/` directory).
  Always upgrade the two packages together.
- Do **not** read this document as claiming: physical Qwen inference has
  been run and verified, RF-22 is fully DONE, Whisper/whisper.cpp is
  integrated, speech recognition is provably fully local, a wake word
  ("Oye App") exists, or Siri/App Intents integration exists. None of these
  are implemented or claimed by this work unit.
- Voice is intentionally never initialized on Web
  (`VoiceInputController.initialize()` returns `false` immediately when
  `kIsWeb` is true) — Web behavior for the assistant is typed-text only.
  Typed input works identically on every platform, with or without voice.
  The local-LLM path has no explicit Web guard and `flutter build web`
  succeeds, but Web behavior for local-LLM inference specifically has not
  been exercised or validated in this work unit — treat it as untested on
  Web, not as confirmed working or confirmed disabled.
