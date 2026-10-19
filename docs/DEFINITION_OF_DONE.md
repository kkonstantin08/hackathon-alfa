# Definition of Done — an Issue is complete when

## Functional readiness

- [ ] Linked GitHub Issue has explicit, observable acceptance criteria.
- [ ] Implemented behavior matches the accepted MVP scope in `docs/REQUIREMENTS.md`.
- [ ] Happy path and important failures are demonstrated or tested.
- [ ] Any affected cross-module contracts and dependent owners are updated/notified.

## Engineering readiness

- [ ] Relevant tests, linting, type checks and builds pass locally (once configured for the stack).
- [ ] `CI / foundation` and all added application checks are green on the PR.
- [ ] No credentials, secrets or personal `ROLE.local.md` files were committed.
- [ ] Relevant setup, API, environment and demo instructions are updated.
- [ ] PR states what changed, how it was verified, which Issue is addressed and any risk.

## Merge and demo readiness

- [ ] Normal merge: at least one other person's approving review. Emergency: explicit human authorization and reason recorded in the PR; CI still green.
- [ ] Human gives **explicit command to merge**; agent does not decide to merge autonomously.
- [ ] After merge to `main`, automatic demo deployment succeeds **if configured**; demo URL/health checked.
- [ ] Issue closed or status updated, with `docs/STATUS.md` refreshed at the next checkpoint.

## Definition of demo-ready

- [ ] End-to-end core user journey works in the actual deployed environment.
- [ ] Team knows the demo URL, launch steps, sample data and fallback plan.
- [ ] No open blocker threatens the main demo journey.

