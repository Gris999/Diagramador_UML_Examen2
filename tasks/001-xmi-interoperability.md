# Task 001 - XMI interoperability

## Objective

Implement bidirectional XMI interoperability between the CASE platform and Enterprise Architect.

Primary target:

- UML/XMI 2.1 compatible structure.

## Supported UML subset

- Class
- Attribute / Property
- Operation
- Association
- Aggregation
- Composition
- Generalization
- Dependency
- Multiplicity

## Export

Endpoint:

`POST /api/xmi/export/`

Input:

- internal UML JSON

Output:

- XML/XMI file
- content type: application/xml

## Import

Endpoint:

`POST /api/xmi/import/`

Input:

- XMI/XML file using multipart form field `file`

Output:

- internal UML JSON

## Round-trip requirement

The following flow must preserve semantic model data:

internal JSON -> XMI -> internal JSON

Preserve:

- class names
- attributes and types
- methods
- relationship types
- relationship direction
- multiplicities

Visual JointJS positions and vertices are not required in the first XMI MVP.

## Tests

At minimum:

1. export class
2. export attributes
3. export operation
4. export association
5. export aggregation
6. export composition
7. export generalization
8. export dependency
9. export multiplicities
10. import equivalent XMI
11. JSON -> XMI -> JSON round trip
12. malformed XMI returns controlled error

## Acceptance criteria

- Django tests pass.
- Existing Gemini tests continue passing.
- No network access is required.
- No AI model is required.
- XML parsing must not execute external entities.
- API endpoints work through Django.
- GAP_MATRIX is updated after verification.


## Current status

Backend XMI MVP implemented and verified.

Completed:

- deterministic JSON → XMI conversion;
- deterministic XMI → JSON conversion;
- class import/export;
- attributes;
- operations;
- association;
- aggregation;
- composition;
- generalization;
- dependency;
- multiplicities;
- namespace-prefix-independent import;
- rejection of malformed XML;
- rejection of DOCTYPE / ENTITY input;
- `POST /api/xmi/export/`;
- `POST /api/xmi/import/`;
- automated backend tests;
- real HTTP export/import round trip.

Verification:

- 26 backend tests passing inside the Django Docker container;
- exported `.xmi` returns HTTP 200;
- imported exported file preserves semantic UML data.

Still pending:

- Angular import/export UI;
- physical interoperability test with Enterprise Architect.

### Test environment

Database-backed Django tests are verified inside `django_backend_UML` because the configured PostgreSQL host `postgres` belongs to the Docker network.

Verification command:

`docker exec django_backend_UML python manage.py test uml_api.tests -v 2`

Pure XMI service tests may also run from the local Python virtual environment because they do not require PostgreSQL.
