# Project Requirements

## Modeling

The platform must support UML 2.5 class/data modeling.

Users must be able to create and edit diagrams manually.

## AI-assisted interaction

The system should support creating or modifying UML through:

- natural-language text;
- image/photo input;
- voice input.

## Collaboration

The platform should support collaborative sessions for approximately 2-3 users.

The collaboration model should distinguish:

- host;
- participants.

It should support:

- synchronization;
- permissions;
- reconnect;
- state recovery.

### Live room roles

- The first active connection in a room is the host; later connections are participants.
- Host and participants keep the same diagram editing permissions.
- Only the current host may remove another participant, and the server verifies that permission.
- When the host disconnects, the longest-connected remaining participant becomes host.
- A reconnect is a new connection and does not restore a prior role or identity.
- Roles exist only for the live room session; they require no account or persistent ownership.

## Interoperability

The system must support bidirectional XMI interoperability with Enterprise Architect.

Required flows:

- platform → XMI → Enterprise Architect;
- Enterprise Architect → XMI → platform.

## Backend generation

The system must generate a backend based on the UML model using:

- Spring Boot;
- PostgreSQL.

It should also produce a usable Postman collection.

## Mobile generation

The system must generate a Flutter application/project from the modeled system.

## Offline mobile behavior

The mobile result should include an offline-capable strategy, including local persistence such as SQLite.

## Local AI

The project should demonstrate or integrate a local/on-device AI capability, particularly for mobile/offline scenarios where feasible.

## Deployment

The final system should have a deployable architecture, including AWS-related deployment/documentation as required by the course.

## Documentation

The project must maintain sufficient engineering documentation, including:

- architecture;
- requirements;
- process/PUDS-related material;
- implementation decisions;
- traceability;
- testing evidence.
