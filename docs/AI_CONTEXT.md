# AI Context

## Purpose

This repository is being evolved from an existing UML diagramming application into a final CASE platform for a Software Engineering I project.

The deadline is close, so work must prioritize an end-to-end demonstrable flow rather than unnecessary architectural perfection.

## Repository structure

### front_generador_bd

Angular frontend.

Important capabilities already observed:

- UML canvas/editor using JointJS;
- class/data modeling UI;
- collaboration-related frontend services;
- signaling / peer-to-peer related code.

### back_generador_bd

Django backend.

Technologies:

- Django 5
- Django REST Framework
- Channels
- Redis
- PostgreSQL

Known capabilities:

- UML persistence/backup;
- WebSocket endpoints;
- collaboration infrastructure;
- Gemini-based UML operations;
- basic Flutter generation.

### back_generator_uml

Spring Boot generator service.

Technologies:

- Spring Boot 3.5
- Java 21
- Maven Wrapper

Known capabilities:

- Spring project generation;
- controller/service/repository templates;
- PostgreSQL configuration generation;
- Postman collection generation.

## Verified local baseline

The local baseline has successfully reached:

- Angular build and dev server;
- Django system check;
- Django container startup;
- Redis PONG;
- PostgreSQL healthy;
- Spring tests/build;
- Spring application startup.

## Local environment decisions

PostgreSQL:

- host: localhost
- host port: 5433
- container port: 5432

Spring generator:

- port: 7001

These differ from the original project because host ports 5432 and 7000 are already occupied.

## AI workflow

Gentle-AI is installed for Codex.

Components configured:

- Engram
- SDD
- skills
- Context7
- GGA

Strict TDD is disabled.

Use SDD mainly for substantial architectural features such as:

- XMI interoperability;
- collaboration semantics;
- offline/local AI.

For ordinary implementation work, keep the process lightweight.

## Engram usage

Store durable information such as:

- architectural decisions;
- bugs and their root causes;
- important repository discoveries;
- conventions;
- completed-task summaries;
- integration constraints.

Do not store entire conversations or huge file dumps.

## Priority principle

The highest priority is a reliable demonstration path:

manual UML
→ AI-assisted UML
→ collaboration
→ save/recover
→ XMI round trip
→ Spring/PostgreSQL/Postman generation
→ Flutter generation
→ offline/local capability

## XMI interoperability decision

The XMI interoperability layer targets UML/XMI 2.1 as the first exchange format for Enterprise Architect compatibility.

The conversion must be deterministic and must not depend on Gemini or any other AI service.

The initial supported subset is:

- classes;
- attributes;
- operations;
- association;
- aggregation;
- composition;
- generalization;
- dependency;
- multiplicities.

Visual layout preservation was added after the first XMI MVP.

The CASE tool stores class position and size in a CASE-specific `xmi:Extension`.
This extension is optional metadata: external UML/XMI tools may ignore it
without affecting the standard UML model.

The extension currently preserves:

- class `x` and `y` position;
- class width and height.

Relationship vertices remain outside the current XMI interoperability scope.

The Angular → XMI → Angular round trip has been manually verified to preserve
class layout. Physical import/export verification with Enterprise Architect
is still pending.
