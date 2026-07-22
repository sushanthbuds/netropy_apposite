# AGENTS.md — Instructions for AI Assistants

**Project:** Netropy VE Automated Provisioning  
**Status:** Draft — pending mentor review

This file tells Cursor, Codex, and other AI assistants how to work in `netropy-lab`. The intern remains responsible for reviewing, understanding, and testing all generated changes.

---

## Project summary

Build a **command-line tool** that reads one **JSON configuration file** and provisions a test lab on a single host:

| VM | NICs | Role |
|----|------|------|
| Netropy VE | 1 mgmt + 2 data | Network emulator |
| Linux-1 | 1 mgmt + 1 data | iperf3 traffic endpoint |
| Linux-2 | 1 mgmt + 1 data | iperf3 traffic endpoint |

Three subnets: **management**, **data-1**, **data-2**. Target platforms: **KVM** (first), then ESXi, then AWS.

**Stack:** OpenTofu + platform providers + cloud-init (Ubuntu) + thin Python CLI.

**Source of truth for requirements:** `project_objective/Netropy-VE-Provisioning-Intern-Project.md`  
**Execution plan:** `plan/Netropy_VE_Provisioning_Workbook_Revised.docx`

---

## Read these files first

Before editing, inspect the files relevant to the task:

| Area | Read first |
|------|------------|
| Any task | `AGENTS.md`, `docs/phase_2/repository-structure.md` |
| Lab design | `project_objective/Netropy-VE-Provisioning-Intern-Project.md`, `project_objective/netropy-topology.svg` |
| JSON / CLI | `config/example-kvm.json`, `cli/netropy_lab/validator.py`, `cli/netropy_lab/cli.py` |
| KVM module | `modules/kvm/main.tf`, `modules/kvm/variables.tf`, `modules/kvm/outputs.tf`, `modules/kvm/cloud-init/` |
| Phase 0 POC | `poc/main.tf`, `poc/README.md` |
| Setup / dev env | `docs/phase_2/setup-verification.md`, `scripts/verify-setup.sh` |
| Security | `docs/phase_2/security-guardrails.md`, `scripts/check-secrets.sh` |
| Git workflow | `docs/phase_2/branch-strategy.md` |

When `README.md` exists at the repo root, read it as well.

---

## Scope rules

- **One narrow task per prompt.** Do not expand scope beyond the stated task.
- **Do not invent Netropy VE behavior.** NIC models, boot mode, management URL, credentials, and driver requirements must come from product documentation or be labeled **Needs Product Confirmation**.
- **Do not add ESXi or AWS modules** unless the task explicitly requests that platform.
- **Match existing conventions** — OpenTofu HCL object syntax (libvirt provider v0.9+), Python style in `cli/`, shell helpers in `modules/kvm/`.
- **Minimize diff size.** Change only what the task requires.

---

## Safety rules

### Secrets and sensitive files

- **Never** commit, paste, or log: SSH private keys, AWS keys, passwords, tokens, or production credentials.
- **Never** commit: `*.tfstate`, `.terraform/`, `lab.auto.tfvars.json`, `generated.auto.tfvars`, or `libvirt-pool/`.
- Prefer environment variables, profiles, or IAM roles over secrets in JSON.
- Redact secrets in command output and documentation.
- Run `./scripts/check-secrets.sh` before committing.

### Destructive commands

Explain impact **before** running or suggesting:

- `tofu destroy` / `./run-destroy.sh`
- `virsh destroy` / `virsh undefine`
- `sudo` on apply scripts (breaks `$HOME` and SSH key paths — **do not use**)

### libvirt / KVM

- Apply scripts use `sg libvirt` — run as normal user, not root.
- Pool permissions may require `scripts/fix-libvirt-permissions.sh` after apply.

---

## Workflow

### Before editing

Provide:

1. Understanding of the task  
2. Files inspected  
3. Assumptions  
4. Proposed files to change  
5. Implementation steps  
6. Tests to run  
7. Risks  

Use investigation-only prompts before proposing fixes when debugging.

### After editing

Provide:

1. Files changed  
2. Commands run  
3. Test results  
4. Manual verification steps  
5. Section labeled: **Verified**, **Assumed**, **Unknown**, **Needs Product Confirmation**  
6. Recommended next task  

**Do not claim success** without running the relevant acceptance test or verification command.

---

## Common verification commands

```bash
# Phase 2 setup checks
./scripts/verify-setup.sh

# JSON validation
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json

# KVM lab (only when task requires provisioning)
cd modules/kvm && ./run-apply.sh
cd modules/kvm && ./run-destroy.sh

# libvirt inspection
virsh -c qemu:///system list --all
virsh -c qemu:///system dominfo netropy-lab-linux1
```

---

## Reusable prompt template

Copy and fill in `[ONE NARROW TASK]`:

```
Read AGENTS.md, docs/phase_2/repository-structure.md, and the relevant files.
Current task: [ONE NARROW TASK].

Do not expand scope, invent Netropy behavior, expose secrets, or run destructive
commands without explaining them.

Before editing, provide your understanding, files inspected, assumptions,
proposed files, implementation steps, tests, and risks.

After implementation, list files changed, commands run, test results, manual
verification, verified facts, assumptions, and recommended next task.
```

---

## Current implementation status

| Component | Status |
|-----------|--------|
| Phase 0 POC (`poc/`) | Done — single Ubuntu VM on KVM |
| KVM module (`modules/kvm/`) | In progress — 3 networks, 2 Linux VMs; Netropy gated on image |
| CLI (`cli/`) | Scaffold — `validate`, `up`, `down` |
| ESXi / AWS modules | Not started |
| `verify` command | Not started |

Netropy provisioning uses `options.provision_netropy: false` until `netropy-ve.qcow2` is available.

---

## Mentor sign-off

| Field | Value |
|-------|-------|
| Approved by | ____________________ |
| Date | ____________________ |
| Notes | ____________________ |
