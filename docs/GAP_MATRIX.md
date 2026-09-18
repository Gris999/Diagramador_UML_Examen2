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
| Text → UML | VERIFY | Gemini integration exists; API/model compatibility must be tested |
| Image/photo → UML | VERIFY | Gemini image flow exists; needs current API validation |
| Voice → UML/editing | MISSING | No confirmed implementation |
| Real-time collaboration | PARTIAL | Channels/WebSocket/P2P infrastructure exists |
| 2-3 collaborative users | VERIFY | Needs end-to-end multi-client test |
| Host/participant roles | MISSING | No complete formal role model confirmed |
| Collaboration permissions | PARTIAL | Needs explicit semantics and testing |
| Reconnection | PARTIAL | Infrastructure exists; behavior must be verified |
| State recovery | PARTIAL | BackupUML exists; reconnect recovery must be integrated/tested |
| XMI export | MISSING | High-priority feature |
| XMI import | MISSING | High-priority feature |
| Enterprise Architect round trip | MISSING | Depends on XMI import/export |
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
