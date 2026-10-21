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
| Many-to-many as a visual junction entity | DONE | Only `association` links with `*` on both ends are replaced by an intermediate class (deterministic ids that include the original link id; parallel and reflexive M:N supported) plus two 1:N legs; if a leg stops being "many" the original association is restored. Derived-cell flags travel in collaboration operations. Covered by `diagram.service.junction.spec.ts`, `collaboration.service.spec.ts`, Flutter and XMI tests |
| Participant identity (RF-23) | DONE | Anonymous token + display name in `localStorage` (memory fallback, SSR-safe); `hello` validated by the server; names in the presence snapshot (late joiners see them). Verified with two browsers locally and on https://diagramador.dev on 2026-10-21 |
| Room activity log (RF-25, RNF-06) | DONE | Server-side whitelist (`add_class`, `delete`, `add_link`, `edit_text`), coalescing of repeated edits (5 s), per-connection rate cap and size cap, REST history (the latest events) and live delivery. Move/resize are never logged |
| AI as a room member (RF-24) | DONE | Fixed "IA" row in the participants panel with live status ("Pensando (a pedido de X)") shared with the room |
| Private per-person AI chat (RF-26, RF-27, RNF-04) | DONE | `POST /api/rooms/<room>/ia/chat/` and `GET /api/rooms/<room>/chat/` identified by `X-Participant-Token`; context = diagram + room activity + only the requester's own history. Privacy covered by tests (including a mutation check) |
| AI changes on request (RF-28, RF-29) | DONE | `Pedir cambio` mode: the requester's browser applies the changes through the normal edit path; operations carry `via_ia` and the log shows "IA … (a pedido de X)". `Preguntar`/`Revisar` never return changes (tested with a provider that returns a diagram) |
| AI review and shared suggestions (RF-30) | DONE | `Revisar` publishes an event for the whole room with up to 5 ideas; anyone can apply one (applied by the clicker, marked as applied for everyone) |
| Resume a session (RF-31) | DONE | Verified locally on 2026-10-21: after every participant left, reopening the room restored the diagram (auto-saved snapshot), the activity history and the participant's own AI chat (token kept in the browser). Privacy of other people's chats is covered by tests |
| Mobile follow-along view (RF-32) | MISSING | Planned for I5 (read-only live view) |
| Configurable AI provider / local model (RF-33) | MISSING | Optional; the chat already goes through an `AIProvider` interface (I6) |
| AWS deployment | PARTIAL | Desplegado en AWS EC2 con Docker Compose, nginx y HTTPS (Let's Encrypt) en https://diagramador.dev; procedimiento manual y repetible en `docs/DESPLIEGUE.md`. Faltan infraestructura como código y CI/CD |
| Automated tests | PARTIAL | Frontend 139 specs and Django 74+ tests green on 2026-10-21 (previous 3 failing frontend specs fixed); Spring covered by `ProjectGeneratorCompileTest`; coverage of the new AI/collaboration features is in place, end-to-end browser validation is manual |
| PUDS/process documentation | PARTIAL | Artifacts organized by discipline in `docs/puds/` following the course material (requirements, analysis, design, implementation, tests, with milestones per phase); pending: final test evidence and the instructor's template if one exists |
| Secrets/configuration hygiene | PARTIAL | Secretos en `.env` fuera de git, `DEBUG` apagado en producción y contraseña de Postgres retirada de `back_generador_bd/docker-compose.yml`. La contraseña anterior sigue en el historial de git (público): cambiarla si se usa en otro sitio |
| Reproducible local startup | DONE | Baseline stack verified locally |
