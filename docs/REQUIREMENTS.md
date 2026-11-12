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
- **RF-17** — Roles exist only for the live room session; they require no account or persistent ownership. *(Scope clarified on 2026-11-09: this is about the live roles host/participant, which are still ephemeral. Who may open a room at all, and as what, is decided by the accounts and sharing requirements RF-36 to RF-41.)*

## AI as a room participant

Requested by the instructor on 2026-10-13: the AI becomes one more member of the collaborative board. It does nothing until someone asks, its ideas are visible, it knows what everyone did, and sessions can be resumed. Details and design in `docs/PLAN_PUDS_IA_PARTICIPANTE.md`.

- **RF-23** — Each participant has a visible name and an anonymous identifier kept in their browser.
- **RF-24** — The AI appears as a member in the participants panel.
- **RF-25** — Each room has an activity log, visible to everyone, with author, type and summary of each meaningful action.
- **RF-26** — Each room has one conversation with the AI, shared by everyone in the room; every message shows who wrote it. *(Changed on 2026-10-26 from an individual chat per person: the instructor asked for one model and one instance per room, with no private conversations. Refined on 2026-11-10: the room chat is also where people talk to each other (RF-42), and the AI answers only when addressed by name (RF-43).)*
- **RF-27** — The AI answers about any member's activity using the log.
- **RF-28** — The AI changes the diagram only when a participant explicitly orders it; its ideas are shown as suggestions anyone can apply.
- **RF-29** — AI changes are applied and propagated to everyone, labeled "IA, a pedido de X".
- **RF-30** — On request, the AI reviews classes, attributes, methods and relationships.
- **RF-31** — On returning to a room, the diagram, the activity log and the participant's own chat are recovered.
- **RF-32** — A mobile follow-along view exists (live, read-only): `/sala/<room>/seguir`.
- **RF-33** — *(Optional)* The AI provider is configurable: Gemini or local (Ollama/Qwen).
- **RF-34** — The mobile follow-along view can notify the person of each new event of the room (a change or an AI review) through the browser's notifications, only after the person turns them on with a button and only while the page is open.
- **RF-35** — A help assistant, available from the landing page and inside a room, teaches how to use the tool from the tool's own manual (`back_generador_bd/uml_api/knowledge/AYUDA.md`). Its conversation is personal and kept in the browser; it answers only about the tool and has per-person and global usage limits.

## Accounts, access and sharing

Requested by the team on 2026-11-08 and 2026-11-09 (invite by email like draw.io, mandatory sign-in with the email, and a document list with private/public sharing like Google Docs). Controlled by the server switch `AUTH_REQUIRED` (on in production, off by default so that a local checkout still works without mail).

- **RF-36** — With the switch on, a person enters with the email only: the server mails a 6-digit code (valid 10 minutes, 5 attempts) and, once it is typed, gives a signed session of 30 days. There are no passwords. The browser remembers the accounts that signed in (up to five) and goes back to any of them with one click and no code while its session is valid ("Cambiar de cuenta"); every time a signed-in person opens the tool the server hands back a fresh session, so whoever keeps using it is not asked for a code again (30 days counted from the last visit). Requests for codes are limited per email, per address and in total.
- **RF-37** — A room is private by default: only the people on its list (the owner and the people invited by email) can open it, and the server checks it on every API call and on the WebSocket. Inviting sends an email with the link; the same email must be used to sign in.
- **RF-38** — Each person has a role in a room: **owner** (everything, one per room), **editor** (edit and invite) or **reader** (look only). The server enforces it: reads need reader, writes need editor, and a reader's connection is read-only.
- **RF-39** — General access, as in Google Docs: *Restringido* (only the people on the list) or *Cualquiera con el enlace*, as reader or as editor. The link is offered only when the access is public. A person's effective role is the higher of their own role and the link role.
- **RF-40** — «Mis diagramas»: the start page lists, for the email that signed in, the diagrams the person created, was invited to or opened through a public link, with name, role and last opened. The owner can rename (the name shows in the editor top bar) and delete; anyone else can remove it from their own list.
- **RF-41** — A phone never opens the editor: it goes to the read-only follow view (RF-32).

## Room chat and editor aids

Requested by the team on 2026-11-10 after trying the tool with three people at once.

- **RF-42** — The room chat is for the people of the room: a message written to the team is stored in the shared conversation and shown to everyone live, without reloading the page (a notice over the WebSocket tells each browser to re-read it; a closed chat shows a counter of new messages). Messages between people never reach the AI and are limited per person per minute.
- **RF-43** — The AI of the room has a name, **Uma** (also answers to «IA»), and answers only when a message starts with it («Uma, agrega una clase Cliente»). A short yes or no is read as the answer to her proposal only while one is waiting.
- **RF-44** — A change proposed by the AI is shown to the person who asked, over the diagram, as a preview («holograma»: dashed outlines for new classes, relationships and added members, red for what would be deleted) until they apply or discard it; the preview is never part of the diagram (not synchronized, saved or exported).
- **RF-45** — A relationship line can be moved by hand: clicking it shows handles on its segments, dragging a segment moves it, and a double click on the line returns it to the automatic route. Moved routes are synchronized with the room.
- **RF-46** — A class has one of four kinds from UML 2.5: class, abstract class (name in italics), interface (`«interface»`) or enumeration (`«enumeration»`, one value per line), chosen from the palette; and each attribute or method can carry its visibility (`+` public, `-` private, `#` protected, `~` package) written at the start of its line. The kind and the visibility are saved, shared in the room, exported to XMI (`isAbstract`, `uml:Interface`, `uml:Enumeration` with literals, `visibility`) and read back from XMI; interfaces and enumerations are not turned into tables, entities or screens by the code generators.
- **RF-47** — The tool can take a photo of a class diagram with the camera (the computer's or the phone's) from Importaciones → Tomar foto: the person sees the camera, takes the photo, can retake it and uses it; the photo goes through the same image import as a chosen picture (and keeps the visibility sign of each member and the kind of each class: abstract, interface, enumeration) (the AI turns it into a diagram that is edited afterwards with orders to the AI, and the same replace / merge / cancel choice applies). If the camera is not available or not allowed, the device camera can be used from the dialog.
- **RF-48** — The AI of the room attends several people at the same time: up to a number of slots per room that depends on the model (cloud 4; local model with the parallel engine `LOCAL_ENGINE=mlx` 4; local model with Ollama 1, because its MLX runner answers one request at a time), one request per person. When every slot is busy, the other requests are lined up in the room's queue and attended in order of arrival as soon as a slot frees, without anyone having to ask again; each person sees the conversation and who is being attended. A request that waits more than 80 seconds is told to try again. The slots are set by `AI_CONCURRENCY_GEMINI` / `AI_CONCURRENCY_LOCAL`.

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
