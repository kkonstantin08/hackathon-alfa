# Application architecture — high level only

> Complete collectively when the case is known. This document must not become a detailed blueprint for each engineer's internal implementation.

## Goal and constraints

- Application in one sentence: `<what we are building>`
- Required user-facing functionality: `<MVP from REQUIREMENTS.md>`
- Deadline and critical external constraints: `<details>`

## Agreed stack

| Layer | Technology / service | Why / main constraint | Functional owner |
| --- | --- | --- | --- |
| Frontend | `<TBD>` | `<reason>` | `<function>` |
| Backend | `<TBD>` | `<reason>` | `<function>` |
| Storage | `<TBD>` | `<reason>` | `<function>` |
| Shared API/data contracts | `<TBD>` | `<reason>` | `<function>` |
| Hosting / demo | `<TBD>` | `<reason>` | `<function>` |
| CI / testing | `<TBD>` | `<reason>` | `<function>` |

## Major components and data flow

1. `<User enters via ...>`
2. `<Frontend communicates with ...>`
3. `<Backend/storage/external service ...>`
4. `<Result is returned / rendered ...>`

## Monorepo layout (adjust after case)

```text
<repo>/
  apps/<frontend-app>/
  apps/<backend-app>/
  packages/<shared-contracts>/
  docs/
  .github/
```

Do not create unused directories just to match this suggestion.

## Shared agreements

- Canonical interfaces: [CONTRACTS.md](CONTRACTS.md)
- Functional owners: [ROLES.md](ROLES.md)
- Team-wide consequential decisions: [DECISIONS.md](DECISIONS.md)
- Environment and deploy surface: `<URL / provider / env names once chosen>`

## Engineer autonomy

After the initial team decision on this page, the implementing human (with their agent) chooses patterns, dependencies and internal architecture of their module. Put optional module proposals in the Issue or use [PROPOSAL_TEMPLATE.md](PROPOSAL_TEMPLATE.md). Only shared contracts, public behavior, build/deploy requirements, or MVP scope need cross-team coordination.

