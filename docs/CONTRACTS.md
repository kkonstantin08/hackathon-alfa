# Shared contracts

> Only record boundaries that another developer depends on; do not duplicate internal source-code implementation. Update before implementing incompatible shared-interface changes and notify dependent people in GitHub Issue/PR.

## Contract registry

| Contract ID | Provider | Consumers | Interface / schema | Owner | Status |
| --- | --- | --- | --- | --- | --- |
| C-01 | `<service>` | `<app>` | `<method, endpoint, DTO or reference>` | `<@handle>` | Proposed |

## C-01 — `<contract name>`

- Purpose: `<why it exists>`
- Request / input: `<shape, fields, types>`
- Response / output: `<shape, fields, types>`
- Errors / edge cases: `<documented behavior>`
- Compatibility: `<versioning or migration notes>`
- Consumers to notify: `<@handle list>`
- Linked Issues / PRs: `<links>`

## Change protocol

1. Link the proposed change in an Issue and identify all consumers.
2. Notify affected developers **before** breaking changes; discuss a migration or compatibility path if they are blocked.
3. Update this file and tests/fixtures with the same PR as the code change.
4. Report timing and remaining migrations in the PR and, if material, `docs/STATUS.md`.

