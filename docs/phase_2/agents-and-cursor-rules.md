# Phase 2 — AGENTS.md and Cursor Rules

**Phase:** 2, Task 2-4  
**Status:** Draft — pending mentor review

---

## Deliverables

| File | Purpose |
|------|---------|
| [`AGENTS.md`](../../AGENTS.md) | Full instructions for AI assistants working in this repository |
| [`.cursor/rules/netropy-lab.mdc`](../../.cursor/rules/netropy-lab.mdc) | Cursor always-on project rules (summary pointing to AGENTS.md) |

---

## Workbook alignment

Task 2-4 requires:

- [x] Draft `AGENTS.md`
- [x] Cursor/Codex project rules (`.cursor/rules/netropy-lab.mdc`)
- [ ] Submit for **mentor review** (sign-off table in `AGENTS.md`)

Rules encoded from the execution workbook:

- Read AGENTS.md and relevant files first
- One narrow task per prompt
- Plan before implementation (assumptions, files, tests, risks)
- Investigate before fixing
- Never expose credentials or private keys
- Review diffs and commands before execution
- Require Verified / Assumed / Unknown / Needs Product Confirmation
- Do not accept success without running acceptance tests

---

## How to use with Cursor

1. Open the `netropy-lab` folder as the workspace root.
2. Cursor loads `.cursor/rules/netropy-lab.mdc` automatically (`alwaysApply: true`).
3. Start prompts with the reusable template in `AGENTS.md` or reference `AGENTS.md` directly.

---

## Mentor sign-off

| Field | Value |
|-------|-------|
| Approved by | ____________________ |
| Date | ____________________ |
| Notes | ____________________ |
