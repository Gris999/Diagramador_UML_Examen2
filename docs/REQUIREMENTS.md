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
