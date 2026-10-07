# Contributing to SafeGrid

## Branch workflow

```
main
│
├── feature/backend-api     ← Person 1
├── feature/risk-engine     ← Person 2
├── feature/map-ui          ← Person 3
└── feature/offline         ← Person 4
```

Never push directly to `main`. Open a Pull Request and request review.

## Commit style

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add USGS earthquake ingestion
feat: add earthquake risk classification
feat: render GeoJSON risk zones on map
fix: handle missing earthquake coordinates
docs: update API.md with /risk-zones schema
test: add unit tests for magnitude classifier
```

Keep commits focused. One logical change per commit.

## Definition of done

A task is done when:

- [ ] Implementation exists
- [ ] Works with realistic data (not just mocked)
- [ ] Reasonable error handling exists
- [ ] Tested (unit or integration as appropriate)
- [ ] Does not break existing functionality
- [ ] Relevant docs updated (API.md, RISK_MODEL.md, etc.)
- [ ] Branch reviewed and merged via PR

## Pull request process

1. Open a PR against `main` (or a shared feature branch when integrating).
2. Describe what the PR does and link the GitHub issue.
3. At least one other team member must review before merge.
4. Resolve all review comments before merging.

## Issue format

Issues should be specific and actionable:

**Bad:** `Do backend.`

**Good:** `Create USGS ingestion service and normalize earthquake responses into the internal Hazard model.`

Every issue should have:
- An owner
- A milestone or sprint label
- A priority label (P0 / P1 / P2)

## Feature priority labels

| Label | Meaning |
|---|---|
| `P0` | Required for MVP |
| `P1` | Important — implement after MVP is stable |
| `P2` | Optional — attempt only if time permits |

## AI-generated code

AI may be used to accelerate development. Any AI-generated code merged into the repository must be understood by its owner:

- What it does
- Why it exists
- Its dependencies and data flow
- How to modify and debug it

Do not merge large blocks of generated code that nobody can explain.
