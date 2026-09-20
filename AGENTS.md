# AGENTS.md

## Project

This repository is the working base for the final Software Engineering I CASE project.

The original upstream baseline is:
- Repository: Fournext/Diagramador_UML_Examen2
- Baseline tag: baseline-fournext
- Working branch: develop

Do not rewrite the application from scratch. Improve the existing implementation incrementally.

## Main goal

Deliver a CASE platform focused on UML 2.5 class/data modeling with:

- manual UML diagram editing;
- UML creation/editing from natural-language text;
- UML creation from images/photos;
- voice-assisted editing;
- real-time collaboration for 2-3 users;
- host/participant roles and permissions;
- state recovery after disconnect/reconnect;
- bidirectional XMI interoperability with Enterprise Architect;
- Spring Boot + PostgreSQL project generation;
- Postman collection generation;
- Flutter project generation;
- mobile/offline persistence;
- local/on-device AI capability where feasible.

## Existing architecture

Frontend:
- Angular 20
- TypeScript
- JointJS
- Tailwind CSS

Main backend:
- Django 5
- Django REST Framework
- Django Channels
- Redis
- PostgreSQL

Code generator:
- Spring Boot 3.5
- Java 21
- Maven Wrapper

Generated mobile target:
- Flutter / Dart

## Local ports

- Angular local/dev URL: 4200
- Angular SSR container internal port: 4000
- Docker publishes Angular as host 4200 -> container 4000
- Django: 8000
- Redis: 6379
- PostgreSQL host port: 5433
- PostgreSQL container port: 5432
- Spring generator: 7001

Do not change these ports without a concrete reason.

Port 5432 on the host is already used by another project.
Port 7000 on macOS is occupied by ControlCenter/AirPlay.

## Working rules

1. Inspect existing code before changing it.
2. Do not duplicate functionality that already exists.
3. Prefer small, reversible changes.
4. Keep `develop` working.
5. Never commit real API keys, passwords, tokens, `.env`, virtual environments, node_modules, build output, or generated caches.
6. Do not run destructive dependency upgrades without an explicit reason.
7. Do not run `npm audit fix` automatically.
8. Use existing Maven Wrapper instead of requiring global Maven.
9. Add tests for critical behavior.
10. Run the relevant tests/build before declaring work complete.
11. Document important architectural decisions.
12. Save durable discoveries and decisions in Engram.
13. Do not store full conversation transcripts in Engram.
14. One agent should own one implementation task/branch at a time.
15. Avoid broad refactors close to the delivery deadline.
    - Near a delivery deadline, temporary duplication is acceptable when reusing existing logic would require refactoring already-stable generator paths and would materially increase regression risk.
    - Such duplication must be isolated, explicitly documented as intentional, covered by regression tests, and treated as post-delivery technical debt rather than a preferred design.

## Testing expectations

When running Django tests locally from the repository root, use the project virtual environment explicitly:

`back_generador_bd/.venv/bin/python back_generador_bd/manage.py test`

When testing inside Docker, use:

`docker exec django_backend_UML python manage.py test`

Do not assume the system/global Python has Django installed.

Critical features require tests:

- XMI import/export
- collaboration and synchronization
- permissions/roles
- reconnect/state recovery
- code generators
- UML transformations
- offline persistence

Small UI or configuration changes do not require strict TDD.

## Git

- `main` represents the upstream baseline.
- `develop` is the integration branch.
- Feature work should use dedicated branches/worktrees.
- Prefer small commits with one purpose.
- Do not rewrite shared history.

## Documentation

Before significant work, read:

- `docs/AI_CONTEXT.md`
- `docs/REQUIREMENTS.md`
- `docs/GAP_MATRIX.md`

Update the gap matrix when a requirement materially changes status.

## Definition of done

A task is not complete only because code was written.

It should, when applicable:

- compile;
- pass relevant tests;
- integrate with the existing system;
- have no committed secrets;
- preserve existing behavior;
- update documentation if architecture or requirement status changed.


For Django tests that do not require PostgreSQL, local venv execution is allowed:

back_generador_bd/.venv/bin/python back_generador_bd/manage.py test <test-label>

For database-backed Django/API tests in the current development configuration, run them inside the Django container because POSTGRES_HOST=postgres is resolved by the Docker network:

docker exec django_backend_UML python manage.py test

Do not treat failure to resolve the Docker hostname `postgres` from the macOS host as an application test failure.
Do not assume global Python has Django installed.
