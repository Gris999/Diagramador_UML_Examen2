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
  `flutter build apk`, and `flutter build ios --no-codesign` all succeed
  with `speech_to_text: ^7.5.0` present and these permissions applied.
- **Not verified**: actual microphone/speech behavior on a physical iPhone.
  Voice availability depends on platform and runtime support, and on which
  speech-recognition service is installed. **Offline/on-device speech
  recognition is NOT guaranteed** — `speech_to_text` may use a
  network-backed recognizer depending on the OS, device, and language pack
  installed; nothing in this codebase can currently detect or report which
  one was actually used. `VoiceInputController` does not claim otherwise
  anywhere in its code or in the UI; the mic button only appears when
  `initialize()` succeeds at runtime, on native platforms only.
- Voice is intentionally never initialized on Web
  (`VoiceInputController.initialize()` returns `false` immediately when
  `kIsWeb` is true) — Web behavior for the assistant is typed-text only.
  Typed input works identically on every platform, with or without voice.
