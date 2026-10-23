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

Three subnets: **management**, **data-1**, **data-2**. Target platforms: **KVM** (first), then ESXi.

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
| ESXi / Phase 8 | `docs/phase_8/phase8-development-guide.md`, `docs/phase_8/esxi-setup-checklist.md`, `docs/phase_8/kvm-to-vsphere-mapping.md` |
| Wrap-up / Phase 9 | `docs/phase_9/phase9-development-guide.md`, `docs/phase_9/handover-and-backlog.md` |
| Phase 3 POC | `poc/main.tf`, `poc/README.md`, `docs/phase_3/` |
| Setup / dev env | `docs/phase_2/setup-verification.md`, `scripts/verify-setup.sh` |
| Security | `docs/phase_2/security-guardrails.md`, `scripts/check-secrets.sh` |
| Git workflow | `docs/phase_2/branch-strategy.md` |

When `README.md` exists at the repo root, read it as well.

---

## Scope rules

- **One narrow task per prompt.** Do not expand scope beyond the stated task.
- **Do not invent Netropy VE behavior.** NIC models, boot mode, management URL, credentials, and driver requirements must come from product documentation or be labeled **Needs Product Confirmation**.
- **Do not add an ESXi module** unless the task explicitly requests that platform.
- **Match existing conventions** — OpenTofu HCL object syntax (libvirt provider v0.9+), Python style in `cli/`, shell helpers in `modules/kvm/`.
- **Minimize diff size.** Change only what the task requires.

---

## Safety rules

### Secrets and sensitive files

- **Never** commit, paste, or log: SSH private keys, AWS keys, passwords, tokens, or production credentials.
- **Never** commit: `*.tfstate`, `.terraform/`, `lab.auto.tfvars.json`, `generated.auto.tfvars`, or `libvirt-pool/`.
- Prefer environment variables over secrets in JSON.
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

# KVM lab via CLI (Phase 6 — preferred)
PYTHONPATH=cli python3 -m netropy_lab.cli up -c config/example-kvm.json
PYTHONPATH=cli python3 -m netropy_lab.cli verify -c config/example-kvm.json
PYTHONPATH=cli python3 -m netropy_lab.cli down -c config/example-kvm.json

# KVM lab (fallback shell scripts)
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
| Phase 3 POC (`poc/`) | Done — single Ubuntu VM on KVM; write-up in `docs/phase_3/` |
| KVM module (`modules/kvm/`) | Phase 5 done — 3 networks, 2 Linux VMs, Netropy VE 5.1.3 |
| CLI (`cli/`) | Phase 6 done — `validate`, `plan`, `up`, `down`; Phase 7 done — `verify` |
| ESXi module | Phase 8 **wrapped up** — manual Host Client Stage A/B + docs (`docs/phase_8/`); OpenTofu `modules/esxi/` not started (follow-on) |
| `verify` command | Phase 7 KVM; ESXi verify not started |
| Phase 9 wrap-up | **Done** — README + `docs/phase_9/` (demo, handover, limitations); passthrough stretch not implemented |

Netropy on this host (KVM) uses `options.provision_netropy: true` with OVA disk1 + disk2 qcow2 under `Netropy-VM/`. Write-ups: `docs/phase_5/phase5-development-guide.md`, `docs/phase_6/phase6-development-guide.md`. ESXi manual lab uses a separate **OVA** and Bridging; see `docs/phase_8/phase8-development-guide.md`.

---

## Mentor sign-off

| Field | Value |
|-------|-------|
| Approved by | ____________________ |
| Date | ____________________ |
| Notes | ____________________ |
