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
| Text → UML/editing | VERIFY | Gemini receives the current UML snapshot for contextual edits; needs live API validation |
| Image/photo → UML | VERIFY | Gemini image flow now validates MIME type/size and sanitizes provider failures; needs live API validation |
| Voice → UML/editing | VERIFY | Browser recording, Gemini transcription, contextual UML edits, and mocked endpoint coverage are implemented; needs live validation |
| Real-time collaboration | PARTIAL | Channels/WebSocket/P2P infrastructure exists |
| 2-3 collaborative users | VERIFY | Needs end-to-end multi-client test |
| Host/participant roles | MISSING | No complete formal role model confirmed |
| Collaboration permissions | PARTIAL | Needs explicit semantics and testing |
| Reconnection | PARTIAL | Infrastructure exists; behavior must be verified |
| State recovery | PARTIAL | BackupUML exists; reconnect recovery must be integrated/tested |
| XMI export | DONE | Backend and Angular export verified; CASE-specific XMI extension preserves class position and size |
| XMI import | DONE | Backend and Angular import verified; class position and size are restored when CASE layout metadata is present |
| Enterprise Architect round trip | DONE | Physical UML/XMI 2.1 round trip verified with Enterprise Architect 17.2 in both directions; classes, attributes/types, operations, associations and multiplicities preserved |
| Spring Boot generation | VERIFY | Generator exists and Spring service runs |
| PostgreSQL generation | VERIFY | Templates/configuration exist |
| Postman generation | VERIFY | Generator implementation exists |
| Generated Spring project compiles | MISSING | Need generated-project integration test |
| Flutter generation | PARTIAL | Basic generator exists |
| SQLite/offline Flutter persistence | MISSING | Required extension |
| Local/on-device mobile AI | MISSING | Required MVP/design |
| AWS deployment | PARTIAL | Needs current deployment path/evidence |
| Automated tests | PARTIAL | Existing coverage is insufficient for final requirements |
| PUDS/process documentation | PARTIAL | Needs final alignment |
| Secrets/configuration hygiene | PARTIAL | Hard-coded settings remain |
| Reproducible local startup | DONE | Baseline stack verified locally |
