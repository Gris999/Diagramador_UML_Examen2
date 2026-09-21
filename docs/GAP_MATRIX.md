# Gap Matrix

Status values:

- DONE: implemented and verified
- PARTIAL: some implementation exists but requirement is incomplete
- MISSING: no meaningful implementation found yet
- VERIFY: implementation appears to exist but needs end-to-end validation

| Requirement | Current status | Notes |
|---|---|---|
| Manual UML editor | DONE | Existing Angular + JointJS editor |
| Web DELETE | DONE | Physical two-tab validation passed: class deletion syncs across collaborators, deleting a class removes its connected relationships while preserving unrelated classes, relationship-only deletion preserves both classes, and deleted content does not reappear after reload/rejoin |
| Diagram image/PNG export | DONE | Physical export validation passed with explicit #f8f9fa background, visible diagram content, and no application UI chrome in the exported image |
| UML 2.5 class/data modeling | PARTIAL | Existing class modeling; formal UML 2.5 coverage must be validated |
| Text → UML/editing | DONE | Real Google Gemini runtime validated class creation plus existing-class attribute and method edits with stable JointJS identity, no duplication, and preserved layout |
| Image/photo → UML | DONE | Physical Gemini validation recognized classes, attributes, methods, and relationships; class auto-width, Manhattan routing, Replace/Merge/Cancel/Escape, and two-tab Replace synchronization passed |
| Voice → UML/editing | DONE | Physical Chrome microphone validation passed class creation plus same-class attribute and method edits with prior content retained and no duplicate class |
| Real-time collaboration | DONE | The early ICE-before-SDP race was fixed; repeated 2-peer, 3-peer convergence, adversarial/jitter, and post-fix smoke validation passed |
| 2-3 collaborative users | DONE | Physical 3-client validation passed join order, shared-state convergence, rejoin, and role behavior |
| Host/participant roles | DONE | Real Redis-backed 3-client validation confirmed first-host assignment, ordered participant state, longest-connected promotion, and reconnect as participant |
| Collaboration permissions | DONE | Real 3-client validation confirmed participant removal denial, host-only kick with socket closure, correct UI controls, and continued collaboration afterward |
| Reconnection | DONE | Repeated WebRTC rejoin validation passed; a former host reconnects as participant when another host exists, and deleted content stays deleted |
| State recovery | DONE | Shared diagram recovery passed after rejoin, deletion, and Image → UML Replace |
| XMI export | DONE | Backend and Angular export verified; CASE-specific XMI extension preserves class position and size |
| XMI import | DONE | Backend and Angular import verified; class position and size are restored when CASE layout metadata is present |
| Enterprise Architect round trip | DONE | Physical UML/XMI 2.1 round trip verified with Enterprise Architect 17.2 in both directions; classes, attributes/types, operations, associations and multiplicities preserved |
| XMI XXE/network-independence security | DONE | Pre-parse DOCTYPE/ENTITY rejection blocks external entities; local-file and network XXE fixtures were rejected, runtime instrumentation observed zero network connections, and all dedicated XMI tests passed |
| Spring Boot generation | DONE | ProjectGeneratorCompileTest generates the project and runs a real Maven compilation |
| PostgreSQL generation | DONE | Generated templates contain the PostgreSQL driver, dialect, and datasource configuration exercised by generated-project compile coverage |
| Postman generation | DONE | Real generator output is covered by generator integration tests |
| Generated Spring project compiles | DONE | ProjectGeneratorCompileTest unpacks the generated project and successfully executes a real Maven build |
| Flutter generation | DONE | Physical-device validation passed; the generated Flutter application ran successfully with CRUD validated |
| SQLite/offline Flutter persistence | DONE | Physical offline SQLite CRUD and persistence validation passed with data retained |
| Local/on-device mobile AI | PARTIAL | Generated Flutter apps now include a local schema-aware CRUD command assistant and speech-input integration. The command parser is deterministic, not an LLM/AI model; offline/on-device speech and genuine local model inference are still unverified/pending. |
| AWS deployment | DEFERRED | Manual/ad-hoc EC2 groundwork exists, but there is no reproducible IaC/CI-CD production deployment; deferred unless required by the course |
| Automated tests | PARTIAL | Existing coverage is insufficient for final requirements |
| PUDS/process documentation | PARTIAL | Needs final alignment |
| Secrets/configuration hygiene | PARTIAL | Hard-coded settings remain |
| Reproducible local startup | DONE | Baseline stack verified locally |
