# Branch Strategy

**Project:** Netropy VE Automated Provisioning\
**Phase:** 2 — Development Environment and Repository\
**Status:** Draft — pending mentor approval

## Overview

This repository uses a simple **trunk-based workflow** suited to an intern-scale project: one stable branch plus short-lived feature branches for focused work.

The workbook requires a **documented, mentor-approved** branch strategy. Update the status line above after your mentor reviews this file.

## Branches

| Branch | Required | Purpose |
|----|----|----|
| `main` | Yes | Stable, working code. All phase deliverables merge here. |
| `feature` | As needed | One focused task or phase item (e.g. `feature/phase4-json-validation`). |

There is **no fixed number of branches**. You always have `main`; create feature branches only when useful.

## Workflow

1.  Create a feature branch from `main`:

    ```bash
    git checkout main
    git pull
    git checkout -b feature/phase2-setup
    ```

2.  Make **small, focused commits** with clear messages:

    ```bash
    git add <files>
    git commit -m "Add branch strategy doc for Phase 2"
    ```

3.  Open a **pull request** for mentor review (when using GitHub), or ask your mentor to review locally before merging.

4.  Merge to `main` after approval. Delete the feature branch when done.

5.  Tag baseline milestones on `main` (e.g. `v0.1.0-baseline` after Phase 2).

## Rules

- **Never commit secrets** — SSH private keys, AWS keys, passwords, or `lab.auto.tfvars.json`.
- **Never commit generated state** — `*.tfstate`, `.terraform/`, or local pool data (see `.gitignore`).
- **One logical change per commit** — easier to review and revert.
- **Do not force-push to** `main` without mentor approval.

## Default branch

The default branch is `main`.

If the repository was initialized as `master`, rename once before the first commit:

```bash
git branch -m master main
```
