# Repository Structure

**Phase:** 2, Task 2-3  
**Project:** Netropy VE Automated Provisioning  
**Status:** Complete

This document describes the top-level layout of `netropy-lab` and the purpose of each directory.

---

## Directory tree

```
netropy-lab/
├── cli/                  Python CLI wrapper
├── config/               Example JSON lab configurations
├── docs/                 Phase deliverables and technical notes
├── images/               VM disk images (not all committed to git)
├── modules/
│   └── kvm/              OpenTofu libvirt module (KVM platform)
├── plan/                 Intern execution workbook
├── poc/                  Phase 0 single-VM proof-of-concept
├── project_objective/    Original project specification
├── scripts/              Helper and verification scripts
├── libvirt-pool/         Runtime libvirt storage (gitignored)
└── README.md             Project overview (Phase 2, Task 2-6)
```

Future platforms will add `modules/esxi/` and `modules/aws/` when implemented.

---

## Top-level directories

| Directory | Purpose |
|-----------|---------|
| **`cli/`** | Thin Python CLI that validates JSON, selects the platform module, generates OpenTofu variables, runs `tofu apply`/`destroy`, and prints an access summary. Entry point: `netropy-lab`. |
| **`config/`** | Example JSON configuration files describing a lab (subnets, IPs, images, options). Start with `example-kvm.json`. |
| **`docs/`** | Written deliverables organized by internship phase (`phase_0/`, `phase_1/`, `phase_2/`, …). Includes tool recommendations, architecture notes, setup verification, and branch strategy. |
| **`images/`** | Local VM images used by OpenTofu modules — Ubuntu cloud image (`noble-server-cloudimg-amd64.img`) and Netropy VE qcow2 when available. Large binaries may stay on disk only and not be committed. |
| **`modules/`** | OpenTofu infrastructure modules, one subdirectory per target platform. |
| **`modules/kvm/`** | Full KVM lab: three libvirt networks, two Ubuntu endpoints, optional Netropy VE VM. Contains `main.tf`, variables, outputs, cloud-init templates, and `run-apply.sh` / `run-destroy.sh`. |
| **`plan/`** | Netropy VE Provisioning execution workbook (phase checklist and mentor guidance). Reference material, not executed at runtime. |
| **`poc/`** | Phase 0 proof-of-concept: boots one Ubuntu VM on KVM using OpenTofu + libvirt + cloud-init. Used to validate the tool stack before building the full lab. |
| **`project_objective/`** | Original intern project requirements (`Netropy-VE-Provisioning-Intern-Project.md`) and topology diagram (`netropy-topology.svg`). Source-of-truth for lab design. |
| **`scripts/`** | Standalone helper scripts — e.g. `verify-setup.sh` (Phase 2 setup checks), `fix-libvirt-permissions.sh` (QEMU pool permissions). |

---

## Runtime / generated paths (not source code)

These paths may exist locally but are excluded from version control (see `.gitignore`):

| Path | Purpose |
|------|---------|
| **`libvirt-pool/`** | libvirt storage pool used by the POC (optional local path). |
| **`modules/kvm/.terraform/`** | OpenTofu provider plugins and module cache. |
| **`modules/kvm/*.tfstate`** | OpenTofu state — tracks provisioned resources. |
| **`modules/kvm/lab.auto.tfvars.json`** | Generated from JSON config by CLI or apply script; may contain SSH public keys. |
| **`cli/**/__pycache__/`** | Python bytecode cache. |

Production KVM apply uses `/var/lib/netropy-lab-pool` for the libvirt pool and may copy the Ubuntu image to `/var/lib/netropy-lab-images/` (see `modules/kvm/run-apply.sh`).

---

## How the pieces fit together

```
project_objective/          plan/
  (what to build)             (how to execute phases)
         │                           │
         └───────────┬───────────────┘
                     ▼
              config/*.json  ──►  cli/  ──►  modules/<platform>/
                     │              │              │
                     │              │              ▼
                     │              │         OpenTofu + libvirt
                     │              │              │
                     │              └──────►  access summary
                     │
              docs/phase_*/  (deliverables & evidence)
```

1. **`project_objective/`** defines the lab topology and acceptance criteria.
2. **`config/`** holds the JSON input for a specific lab instance.
3. **`cli/`** validates JSON and invokes the correct **`modules/<platform>/`** OpenTofu code.
4. **`modules/kvm/`** creates networks, VMs, and cloud-init disks on libvirt.
5. **`docs/`** stores phase write-ups and verification evidence.
6. **`poc/`** remains as the original one-VM stack validation; not used for the full lab.

---

## Key files by task

| If you want to… | Look in… |
|-----------------|----------|
| Change lab IPs or subnets | `config/example-kvm.json` |
| Add KVM resources | `modules/kvm/main.tf` |
| Change Ubuntu guest bootstrap | `modules/kvm/cloud-init/` |
| Add JSON validation rules | `cli/netropy_lab/validator.py` |
| Run setup checks | `scripts/verify-setup.sh` |
| Read phase deliverables | `docs/phase_0/`, `docs/phase_1/`, `docs/phase_2/` |
