# Gap Matrix

Status values:

- DONE: implemented and verified
- PARTIAL: some implementation exists but requirement is incomplete
- MISSING: no meaningful implementation found yet
- VERIFY: implementation appears to exist but needs end-to-end validation

| Requirement | Current status | Notes |
|---|---|---|
| Manual UML editor | DONE | Existing Angular + JointJS editor |
| UML 2.5 class/data modeling | PARTIAL | Existing class modeling; formal UML 2.5 coverage must be validated |
| Text → UML/editing | DONE | Real Google Gemini runtime validated class creation plus existing-class attribute and method edits with stable JointJS identity, no duplication, and preserved layout |
| Image/photo → UML | VERIFY | The UI/backend/Gemini image path exists with MIME/size validation and sanitized failures; live image understanding remains NOT_VERIFIED without a controlled fixture |
| Voice → UML/editing | VERIFY | The MediaRecorder → backend → Gemini contextual-edit pipeline is implemented; physical microphone input remains MANUAL_REQUIRED |
| Real-time collaboration | PARTIAL | Channels/WebSocket/P2P infrastructure exists |
| 2-3 collaborative users | VERIFY | Needs end-to-end multi-client test |
| Host/participant roles | DONE | Real Redis-backed 3-client validation confirmed first-host assignment, ordered participant state, longest-connected promotion, and reconnect as participant |
| Collaboration permissions | DONE | Real 3-client validation confirmed participant removal denial, host-only kick with socket closure, correct UI controls, and continued collaboration afterward |
| Reconnection | PARTIAL | Infrastructure exists; behavior must be verified |
| State recovery | PARTIAL | BackupUML exists; reconnect recovery must be integrated/tested |
| XMI export | DONE | Backend and Angular export verified; CASE-specific XMI extension preserves class position and size |
| XMI import | DONE | Backend and Angular import verified; class position and size are restored when CASE layout metadata is present |
| Enterprise Architect round trip | DONE | Physical UML/XMI 2.1 round trip verified with Enterprise Architect 17.2 in both directions; classes, attributes/types, operations, associations and multiplicities preserved |
| Spring Boot generation | VERIFY | Generator exists and Spring service runs |
| PostgreSQL generation | VERIFY | Templates/configuration exist |
| Postman generation | VERIFY | Generator implementation exists |
| Generated Spring project compiles | MISSING | Need generated-project integration test |
| Flutter generation | VERIFY | Generator now emits models, CRUD services/views, SQLite offline persistence, M:N intermediate entities, and a schema-aware text/voice command assistant. Generated tests plus Web/APK/iOS builds pass; physical-device validation remains pending. |
| SQLite/offline Flutter persistence | VERIFY | Implemented in the Flutter generator with SQLite DatabaseHelper and network-first/local-fallback services; generator tests and Web/APK/iOS builds pass. Physical offline runtime demo pending. |
| Local/on-device mobile AI | PARTIAL | Generated Flutter apps now include a local schema-aware CRUD command assistant and speech-input integration. The command parser is deterministic, not an LLM/AI model; offline/on-device speech and genuine local model inference are still unverified/pending. |
| AWS deployment | PARTIAL | Needs current deployment path/evidence |
| Automated tests | PARTIAL | Existing coverage is insufficient for final requirements |
| PUDS/process documentation | PARTIAL | Needs final alignment |
| Secrets/configuration hygiene | PARTIAL | Hard-coded settings remain |
| Reproducible local startup | DONE | Baseline stack verified locally |
