# Phase 2 — Development Instructions Guide

**Project:** Netropy VE Automated Provisioning  
**Phase:** 2 — Set Up the Development Environment and Repository  
**Related write-ups:** `docs/phase_2/*.md`  
**Baseline tag:** `v0.1.0-baseline`  

---

## 1. Purpose of Phase 2

Phase 2 prepares a **safe, repeatable workspace** before building the provisioning tool.

You must be able to:

1. **Verify the dev host** — Python, OpenTofu, KVM/libvirt, Ubuntu image  
2. **Organize the repository** — clear folder layout and README  
3. **Work safely with git** — branch strategy, no secrets in commits  
4. **Use AI assistants correctly** — AGENTS.md and Cursor rules  
5. **Operate libvirt basics** — list, inspect, start, stop VMs  

**Exit gate (workbook):** A fresh shell can run `./scripts/verify-setup.sh` and all required checks **PASS**.

Phase 2 does **not** complete the full Netropy lab or final CLI — it sets up the foundation.

---

## 2. Phase 2 deliverables (workbook tasks)

| Task | Deliverable | Location |
|------|-------------|----------|
| 2-1 | Git repo + branch strategy | `docs/phase_2/branch-strategy.md` |
| 2-2 | Setup verification | `docs/phase_2/setup-verification.md`, `scripts/verify-setup.sh` |
| 2-3 | Repository structure | `docs/phase_2/repository-structure.md`, top-level dirs |
| 2-4 | AI assistant rules | `AGENTS.md`, `.cursor/rules/netropy-lab.mdc` |
| 2-5 | Security guardrails | `docs/phase_2/security-guardrails.md`, `scripts/check-secrets.sh` |
| 2-6 | Baseline README | `README.md` |
| 2-7 | libvirt VM lifecycle demo | `docs/phase_2/libvirt-vm-demo.md` |

---

## 3. Files involved in Phase 2

### Documentation

| Path | Role |
|------|------|
| `docs/phase_2/setup-verification.md` | Record of host tool checks and sample output |
| `docs/phase_2/repository-structure.md` | Explains every top-level directory |
| `docs/phase_2/branch-strategy.md` | Git workflow (`main` + feature branches) |
| `docs/phase_2/security-guardrails.md` | Secrets, tfstate, destroy policy |
| `docs/phase_2/agents-and-cursor-rules.md` | Evidence that AI rules were written |
| `docs/phase_2/libvirt-vm-demo.md` | Hands-on virsh lifecycle evidence |
| `docs/phase_2/phase2-development-guide.md` | This guide |

### Scripts and config

| Path | Role |
|------|------|
| `scripts/verify-setup.sh` | Automated Phase 2 setup checks |
| `scripts/check-secrets.sh` | Pre-commit scan for secrets and forbidden files |
| `scripts/fix-libvirt-permissions.sh` | Fix pool ownership so QEMU can read disks |
| `AGENTS.md` | Full instructions for AI assistants |
| `.cursor/rules/netropy-lab.mdc` | Cursor auto-loaded rules (summary of AGENTS.md) |
| `.gitignore` | Excludes tfstate, keys, pool data, generated tfvars |
| `README.md` | Project overview and quick start |

### Repository layout (created in Phase 2)

```text
netropy-lab/
├── cli/                  Python CLI wrapper
├── config/               Example JSON lab configurations
├── docs/                 Phase deliverables
├── images/               VM disk images (local; large files gitignored)
├── modules/kvm/          OpenTofu libvirt module (full lab — built later)
├── plan/                 Intern execution workbook
├── poc/                  Phase 3 single-VM proof-of-concept
├── project_objective/    Original project specification
├── scripts/              Helper and verification scripts
├── libvirt-pool/         Runtime storage (gitignored)
└── README.md
```

**How pieces relate:** `project_objective/` defines requirements → `config/` holds JSON input → `cli/` validates and invokes OpenTofu → `modules/kvm/` provisions on libvirt → `scripts/` verifies the host → `docs/` stores phase evidence.

---

## 4. Prerequisites — install tools on the dev host

Run on Ubuntu/Debian if setup checks fail.

### 4.1 Core tooling

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv
```

**Why:** Python runs the CLI (`cli/netropy_lab/`).  
**How:** `python3 --version` should show 3.10+.

### 4.2 OpenTofu

Install from [https://opentofu.org/docs/intro/install/](https://opentofu.org/docs/intro/install/) (not covered by default apt on all distros).

```bash
tofu version
```

**Why:** All KVM provisioning uses OpenTofu (`tofu init`, `apply`, `destroy`).  
**How:** Expect OpenTofu >= 1.6 (verified with v1.12.x).

### 4.3 KVM / libvirt

```bash
sudo apt install -y qemu-kvm libvirt-daemon-system virtinst bridge-utils cpu-checker
sudo usermod -aG libvirt,kvm "$USER"
# log out/in, or:
newgrp libvirt
```

| Command | Why |
|---------|-----|
| `qemu-kvm`, `libvirt-daemon-system` | Hypervisor and management daemon |
| `virtinst` | VM installation helpers (optional for manual work) |
| `cpu-checker` | Provides `kvm-ok` |
| `usermod -aG libvirt,kvm` | Lets your user talk to libvirt without sudo |

### 4.4 Optional host cloud-init utilities

```bash
sudo apt install -y cloud-init cloud-image-utils
```

**Why optional:** Guest cloud-init runs **inside** VMs via ISOs created by the libvirt provider. Host `cloud-init` CLI is useful for debugging YAML locally, not required for the KVM workflow.

### 4.5 Ubuntu cloud image

```bash
mkdir -p ~/netropy-lab/images
wget -O ~/netropy-lab/images/noble-server-cloudimg-amd64.img \
  https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
```

**Why:** Base disk for Ubuntu VMs in `modules/kvm/` and `poc/`.  
**How:** Large file (~600 MB); stays on disk, typically not committed to git.

---

## 5. Run setup verification (main Phase 2 check)

From repo root:

```bash
cd ~/netropy-lab
chmod +x scripts/verify-setup.sh scripts/check-secrets.sh
./scripts/verify-setup.sh
```

### What `verify-setup.sh` checks

| Section | Commands / checks | Why |
|---------|-------------------|-----|
| Python | `python3 --version`, pip, venv | CLI and tests |
| OpenTofu | `tofu version` | Infrastructure provisioning |
| KVM/libvirt | `virsh`, `groups`, `/dev/kvm`, `kvm-ok`, `qemu:///system` | VM lifecycle on host |
| QEMU | `qemu-system-x86_64 --version` | Actual hypervisor binary |
| cloud-init | host CLI (WARN if missing) | Optional on host |
| Ubuntu image | `images/noble-server-cloudimg-amd64.img` or `/var/lib/netropy-lab-images/` | Guest base image |
| JSON validation | `PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json` | Config scaffold works |

**Exit code 0** = all required PASS lines succeeded. **Exit code 1** = fix failures before proceeding.

Example validation command (also run inside the script):

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json
```

**Why:** Confirms the example JSON matches Phase 1 architecture and passes the CLI validator.  
**Output when OK:** `Config OK: config/example-kvm.json`

---

## 6. Git and branch strategy

Documented in `docs/phase_2/branch-strategy.md`.

### Branches

| Branch | Purpose |
|--------|---------|
| `main` | Stable, working code; phase deliverables merge here |
| `feature/<name>` | Short-lived branches for one focused task |

### Typical workflow

```bash
git checkout main
git pull
git checkout -b feature/phase4-json-validation

# work, commit small logical changes
git add <files>
git commit -m "Add JSON schema for Phase 4"

# after mentor review, merge to main
git checkout main
git merge feature/phase4-json-validation
```

**Why feature branches:** Keeps `main` stable and makes mentor review easier.

### Baseline tag

After Phase 2 baseline commit:

```bash
git tag -a v0.1.0-baseline -m "Phase 2 baseline — dev environment and repository setup"
```

**Why:** Marks a known-good point to return to or reference in docs.

### Rules

- Never commit secrets, `*.tfstate`, or `lab.auto.tfvars.json`  
- One logical change per commit  
- Do not force-push `main` without mentor approval  

---

## 7. Security guardrails

Documented in `docs/phase_2/security-guardrails.md`.

### 7.1 Pre-commit secret check

```bash
./scripts/check-secrets.sh
```

**What it does:**

- Fails if forbidden files are tracked (`lab.auto.tfvars.json`, `.env`, `*.tfstate`)  
- Fails if SSH private keys are tracked  
- Scans tracked text files for patterns like `BEGIN PRIVATE KEY`, AWS secrets, hardcoded passwords  

**Why:** Prevents accidental credential leaks before `git commit`.

### 7.2 Never commit

| Item | Why |
|------|-----|
| SSH private keys | Full host access |
| AWS / ESXi passwords | Cloud/hypervisor access |
| `*.tfstate` | Contains resource IDs and sometimes sensitive attrs |
| `lab.auto.tfvars.json` | Generated; may embed SSH public key and lab values |

### 7.3 JSON config and keys

`config/example-kvm.json` uses:

```json
"ssh_public_key_file": "~/.ssh/id_ed25519.pub"
```

**Why path only:** Private keys never go in JSON or git. CLI reads the public key at runtime.

### 7.4 Destructive commands (understand before running)

| Command | Effect |
|---------|--------|
| `modules/kvm/run-destroy.sh` | Destroys entire KVM lab in OpenTofu state |
| `tofu destroy` | Same — removes all tracked resources |
| `virsh destroy <vm>` | Force power-off one VM |
| `virsh undefine <vm>` | Remove VM definition (can desync OpenTofu) |
| `sudo ./run-apply.sh` | **Do not run** — breaks `$HOME` and SSH key paths |

Safe full teardown:

```bash
cd ~/netropy-lab/modules/kvm
./run-destroy.sh
# type 'destroy' when prompted
```

**Why confirmation:** Prevents accidental lab deletion.

---

## 8. AI assistant setup (AGENTS.md + Cursor)

| File | Role |
|------|------|
| `AGENTS.md` | Full workflow: read first, one task per prompt, plan before code, Verified/Assumed/Unknown sections |
| `.cursor/rules/netropy-lab.mdc` | Cursor loads automatically when workspace is `netropy-lab/` |

**Why:** Keeps AI-generated changes narrow, safe, and aligned with the workbook.

**How to use:** Open `netropy-lab` as workspace root; reference AGENTS.md in prompts; run verification before claiming success.

---

## 9. libvirt VM lifecycle demo (Task 2-7)

All commands use system libvirt: `qemu:///system`.

Demo VM: `netropy-lab-linux1` (and `netropy-lab-linux2`) from `modules/kvm/`.

### 9.1 List all VMs

```bash
virsh -c qemu:///system list --all
```

**Why:** See running and shut-off domains.  
**How:** Asterisk `*` in State column = running.

### 9.2 Inspect one VM

```bash
virsh -c qemu:///system dominfo netropy-lab-linux1
```

**Why:** Shows vCPU, RAM, state, autostart, persistent flag.

### 9.3 Graceful shutdown

```bash
virsh -c qemu:///system shutdown netropy-lab-linux1
sleep 5
virsh -c qemu:///system domstate netropy-lab-linux1
```

**Why:** Sends ACPI shutdown to guest (clean stop).  
**How:** State may show `shut off` after a few seconds.

### 9.4 Start a stopped VM

```bash
virsh -c qemu:///system start netropy-lab-linux1
virsh -c qemu:///system domstate netropy-lab-linux1
```

**Why:** Boot a domain that exists but is not running.

### 9.5 Force power-off (single VM)

```bash
virsh -c qemu:///system destroy netropy-lab-linux1
virsh -c qemu:///system domstate netropy-lab-linux1
```

**Why:** Immediate stop (like pulling power). Use when `shutdown` hangs.  
**Note:** Does **not** remove the VM definition — OpenTofu state stays consistent if you `start` again. **`undefine`** would desync OpenTofu — avoid unless you know the impact.

### 9.6 Start lab VMs (project helper)

```bash
cd ~/netropy-lab/modules/kvm
./run-start.sh
```

**Why:** Starts both Linux lab VMs after a host reboot.

### 9.7 Full lab teardown (OpenTofu)

```bash
cd ~/netropy-lab/modules/kvm
./run-destroy.sh
```

**Why:** Removes all resources defined in `modules/kvm/main.tf` via `tofu destroy`.  
**Warning:** Destroys VMs, networks, and pool resources in state — not used casually during demos.

### Command summary

| Goal | Command |
|------|---------|
| List VMs | `virsh -c qemu:///system list --all` |
| Inspect VM | `virsh -c qemu:///system dominfo <name>` |
| Graceful stop | `virsh -c qemu:///system shutdown <name>` |
| Start VM | `virsh -c qemu:///system start <name>` |
| Force stop | `virsh -c qemu:///system destroy <name>` |
| Start lab VMs | `modules/kvm/run-start.sh` |
| Destroy full lab | `modules/kvm/run-destroy.sh` |

---

## 10. Fix libvirt pool permissions

If VMs fail to boot with disk permission errors:

```bash
./scripts/fix-libvirt-permissions.sh
```

**What it does:**

```bash
sudo chown -R libvirt-qemu:libvirt /var/lib/netropy-lab-pool
sudo chmod 755 /var/lib/netropy-lab-pool
sudo chmod 660 /var/lib/netropy-lab-pool/*
sudo chmod o+x "$HOME" "$HOME/netropy-lab"
# restarts netropy-lab-linux1 and netropy-lab-linux2 if they exist
```

**Why:** QEMU runs as `libvirt-qemu` and must read qcow2 files. Parent directories need traverse (`o+x`) permission.

**When:** After apply if VMs show boot/SSH failures due to permissions.

---

## 11. How Phase 2 connects to later phases

```text
Phase 2 (dev env)  →  verify-setup.sh passes
                  →  Phase 3 POC (poc/)
                  →  Phase 4 JSON validation (cli/)
                  →  Phase 5 full lab (modules/kvm/)
```

| Phase 2 output | Used later in |
|----------------|---------------|
| Repo structure | All code and docs |
| `verify-setup.sh` | Pre-flight before any provisioning |
| `check-secrets.sh` | Every commit |
| AGENTS.md | All AI-assisted development |
| virsh skills | Debugging VMs in Phase 5–7 |

---

## 12. Phase 2 exit criteria (self-check)

You can mark Phase 2 complete when:

- [ ] Git repo exists with documented branch strategy  
- [ ] `./scripts/verify-setup.sh` passes in a fresh shell  
- [ ] Repository structure documented  
- [ ] `AGENTS.md` and `.cursor/rules/netropy-lab.mdc` drafted  
- [ ] Security guardrails documented; `check-secrets.sh` works  
- [ ] `README.md` written; baseline tag `v0.1.0-baseline` on `main`  
- [ ] libvirt demo completed (list, dominfo, shutdown, start, destroy)  
- [ ] You can explain this phase **in your own words**

---

## 13. Explain Phase 2 in your own words (student self-check)

Phase 2 set up my development environment and repository. I verified Python, OpenTofu, and KVM/libvirt on the host, organized the repo folders, wrote git and security rules, and added AI assistant instructions. I learned basic virsh commands to inspect and control VMs. The exit test is that `./scripts/verify-setup.sh` passes — proving the machine is ready to build the provisioning tool in later phases.

---

## 14. Quick command cheat sheet

```bash
# Setup verification
cd ~/netropy-lab
./scripts/verify-setup.sh

# Pre-commit
./scripts/check-secrets.sh

# JSON validation
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json

# libvirt basics
virsh -c qemu:///system list --all
virsh -c qemu:///system dominfo netropy-lab-linux1
virsh -c qemu:///system shutdown netropy-lab-linux1
virsh -c qemu:///system start netropy-lab-linux1

# Fix permissions (if VMs won't boot)
./scripts/fix-libvirt-permissions.sh

# Git feature branch
git checkout -b feature/my-task
```

---

**Document status:** Development instructions for Phase 2 (intern reference).  
**Do not commit:** secrets, private keys, `*.tfstate`, or `lab.auto.tfvars.json`.
