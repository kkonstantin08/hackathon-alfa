# Functional ownership after case reveal

> Fill with the team. Five humans can cover more than five functions. Personal `ROLE.local.md` files remain untracked; this file records only the shared interface for ownership/review routing.

| Function | Responsible GitHub handle | Main area / folders | Reviewer / fallback |
| --- | --- | --- | --- |
| Backend | `<@handle>` | `<paths>` | `<@handle>` |
| Frontend | `<@handle>` | `<paths>` | `<@handle>` |
| UI/UX | `<@handle>` | `<design files and UI>` | `<@handle>` |
| Team Lead / Integration | `<@handle>` | `<integration and scope>` | `<@handle>` |
| DevOps | `<@handle>` | `.github/`, `<infra>` | `<@handle>` |
| Fullstack | `<@handle or shared>` | `<assigned vertical slice>` | `<@handle>` |

## Overlap rules

- Functions may overlap; path ownership is a default review route, not an exclusive edit lock.
- One person must not be their own required reviewer. Pick another human familiar with the affected area.
- If the primary reviewer is absent, choose another teammate for normal review; all five may invoke documented Emergency Merge when appropriate.
- Every cross-team contract change gets an Issue/PR notification to dependent humans, even when the author holds multiple roles.

