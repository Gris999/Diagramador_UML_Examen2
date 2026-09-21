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

**No model is bundled with the app, and none is downloaded automatically.**
The user/developer must import a compatible `.gguf` file themselves, at
runtime, via the "Select GGUF model" control in the assistant view (uses
`file_selector`; the chosen file is copied into the app's own
`path_provider` support directory so it persists across restarts). The
acceptance model used during development was **Qwen2.5-0.5B-Instruct**
(GGUF, Q4-class quantization), but the extractor itself is not tied to any
specific model — any compatible GGUF chat model can be used.

The deterministic `CommandParser` remains the **mandatory fallback** for
every failure mode: no model configured, load failure, inference timeout,
malformed/non-JSON output, or an invalid/unrecognized shape. A generated app
with no model imported behaves exactly as before this feature existed. The
UI only labels a result as coming from local AI ("IA local: ...") when the
local model genuinely produced the command that was used — a fallback
result is never labeled as AI, regardless of why the fallback happened.

### iOS 16.4+ setup

Because the local-LLM native runtime requires iOS 16.4+, run the generated
`tool/configure_ios_local_ai.sh` script once after scaffolding the iOS
platform folder:

```bash
flutter create . --platforms=ios,android,web
tool/configure_ios_local_ai.sh            # applies the 16.4 deployment target
tool/configure_ios_local_ai.sh --verify   # verifies it, without modifying anything
```

The script only touches `ios/Runner.xcodeproj/project.pbxproj` (always) and
`ios/Podfile` (only if present) inside the generated project — it never
touches Flutter SDK files. Note: with Flutter's current default Swift
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

Add these two keys inside the top-level `<dict>`:

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

Without these, the OS will silently deny microphone/speech access and
`VoiceInputController.initialize()` will report the assistant's voice input
as unavailable — the mic button stays hidden and the typed assistant keeps
working normally (this is the intended fail-safe, not a bug).

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
