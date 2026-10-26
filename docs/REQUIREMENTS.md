# Project Requirements

## Modeling

**RF-01** — The platform must support UML 2.5 class/data modeling.

**RF-02** — Users must be able to create and edit diagrams manually.

## AI-assisted interaction

The system should support creating or modifying UML through:

- **RF-03** — natural-language text;
- **RF-04** — image/photo input;
- **RF-05** — voice input.

## Collaboration

**RF-06** — The platform should support collaborative sessions for approximately 2-3 users.

**RF-07** — The collaboration model should distinguish:

- host;
- participants.

It should support:

- **RF-08** — synchronization;
- **RF-09** — permissions;
- **RF-10** — reconnect;
- **RF-11** — state recovery.

### Live room roles

- **RF-12** — The first active connection in a room is the host; later connections are participants.
- **RF-13** — Host and participants keep the same diagram editing permissions.
- **RF-14** — Only the current host may remove another participant, and the server verifies that permission.
- **RF-15** — When the host disconnects, the longest-connected remaining participant becomes host.
- **RF-16** — A reconnect is a new connection and does not restore a prior role or identity.
- **RF-17** — Roles exist only for the live room session; they require no account or persistent ownership.

## AI as a room participant

Requested by the instructor on 2026-10-13: the AI becomes one more member of the collaborative board. It does nothing until someone asks, its ideas are visible, it knows what everyone did, and sessions can be resumed. Details and design in `docs/PLAN_PUDS_IA_PARTICIPANTE.md`.

- **RF-23** — Each participant has a visible name and an anonymous identifier kept in their browser.
- **RF-24** — The AI appears as a member in the participants panel.
- **RF-25** — Each room has an activity log, visible to everyone, with author, type and summary of each meaningful action.
- **RF-26** — Each room has one conversation with the AI, shared by everyone in the room; every message shows who wrote it. *(Changed on 2026-10-26 from an individual chat per person: the instructor asked for one model and one instance per room, with no private conversations.)*
- **RF-27** — The AI answers about any member's activity using the log.
- **RF-28** — The AI changes the diagram only when a participant explicitly orders it; its ideas are shown as suggestions anyone can apply.
- **RF-29** — AI changes are applied and propagated to everyone, labeled "IA, a pedido de X".
- **RF-30** — On request, the AI reviews classes, attributes, methods and relationships.
- **RF-31** — On returning to a room, the diagram, the activity log and the participant's own chat are recovered.
- **RF-32** — A mobile follow-along view exists (live, read-only): `/sala/<room>/seguir`.
- **RF-33** — *(Optional)* The AI provider is configurable: Gemini or local (Ollama/Qwen).
- **RF-34** — The mobile follow-along view can notify the person of each new event of the room (a change or an AI review) through the browser's notifications, only after the person turns them on with a button and only while the page is open.
- **RF-35** — A help assistant, available from the landing page and inside a room, teaches how to use the tool from the tool's own manual (`back_generador_bd/uml_api/knowledge/AYUDA.md`). Its conversation is personal and kept in the browser; it answers only about the tool and has per-person and global usage limits.

Additional non-functional requirements:

- **RNF-04** — *(Replaced on 2026-10-26.)* The AI serves one request at a time per room; if it is busy the next person is told who it is attending. The conversation is public to the room, so there is no chat privacy requirement any more.
- **RNF-05** — Resilience: if the AI fails, a clear message is shown and the diagram is neither lost nor corrupted.
- **RNF-06** — The activity log must not degrade editing: continuous actions (move, resize) are not logged.
- **RNF-07** — Deployment is reproducible and has a smoke test.
- **RNF-08** — The room activity and the AI conversation are documents that are only appended to, so they can be stored in a document database (MongoDB) instead of PostgreSQL by configuration (`ACTIVITY_STORE`, `CONVERSATION_STORE`), behind ports and adapters; participants stay relational (PostgreSQL) and ephemeral state in Redis. `python manage.py migrar_a_mongo` copies the existing history.

## Interoperability

**RF-18** — The system must support bidirectional XMI interoperability with Enterprise Architect.

Required flows:

- platform → XMI → Enterprise Architect;
- Enterprise Architect → XMI → platform.

## Backend generation

**RF-19** — The system must generate a backend based on the UML model using:

- Spring Boot;
- PostgreSQL.

**RF-20** — It should also produce a usable Postman collection.

## Mobile generation

**RF-21** — The system must generate a Flutter application/project from the modeled system.

## Offline mobile behavior

**RNF-01** — The mobile result should include an offline-capable strategy, including local persistence such as SQLite.

## Local AI

**RF-22** — The project should demonstrate or integrate a local/on-device AI capability, particularly for mobile/offline scenarios where feasible.

## Deployment

**RNF-02** — The final system should have a deployable architecture, including AWS-related deployment/documentation as required by the course.

## Documentation

**RNF-03** — The project must maintain sufficient engineering documentation, including:

- architecture;
- requirements;
- process/PUDS-related material;
- implementation decisions;
- traceability;
- testing evidence.
