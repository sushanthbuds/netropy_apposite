# Netropy Lab

Automated provisioning of a **Netropy Virtual Edition (VE)** test lab from a single JSON configuration file.

**Lab topology:** 1 Netropy VE + 2 Ubuntu Linux traffic endpoints on three subnets (management, data-1, data-2).

**Target platforms:** KVM (automated) · ESXi (manual POC)

---

## Status

| Component | Status |
|-----------|--------|
| Phase 1 architecture | Done — `docs/phase_1/` |
| Phase 2 dev environment | Done — `docs/phase_2/` |
| Phase 3 tool selection + POC | Done — `poc/`, `docs/phase_3/` |
| Phase 4 JSON contract | Done — `docs/phase_4/` |
| Phase 5 full KVM lab | Done — `modules/kvm/`, `docs/phase_5/` |
| Phase 6 CLI (`validate`, `plan`, `up`, `down`) | Done — `cli/`, `docs/phase_6/` |
| Netropy VE 5.1.3 | Working — virtio × 3, host-passthrough, two SATA disks |
| Phase 7 `verify` command | Done — `cli/netropy_lab/verify.py`, `docs/phase_7/` |
| Phase 8 ESXi | **Wrapped up** (manual POC + docs) — `docs/phase_8/` (OpenTofu follow-on) |
| Phase 9 wrap-up | **Done** — `docs/phase_9/` (demo, handover, limitations; passthrough not implemented) |

Baseline tag: **`v0.1.0-baseline`**

**New user exit gate (Phase 9):** follow **Quick start (KVM)** below to validate → up → verify → down. Demo script: [`docs/phase_9/demo-script.md`](docs/phase_9/demo-script.md).

---

## Prerequisites

### KVM (primary — automated)

- Linux host with **KVM** and **libvirt** (`kvm-ok` passes)
- User in the **`libvirt`** group
- **OpenTofu** >= 1.6
- **Python** >= 3.10
- Ubuntu 24.04 cloud image at `/var/lib/netropy-lab-images/noble-server-cloudimg-amd64.img`
- Netropy VE 5.1.3 qcow2 pair (disk1 + disk2) when `provision_netropy` is `true`

See `docs/phase_2/setup-verification.md` and `docs/phase_9/known-limitations.md` for versions.

### ESXi (manual only)

- Company VPN + Host Client access; see `docs/phase_8/esxi-setup-checklist.md`
- OpenTofu `modules/esxi/` is **not** implemented

---

## Setup verification

From a fresh shell at the repo root:

```bash
chmod +x scripts/verify-setup.sh scripts/check-secrets.sh
./scripts/verify-setup.sh
./scripts/check-secrets.sh
```

All required checks must **PASS** before provisioning.

---

## Repository layout

| Path | Purpose |
|------|---------|
| `ansible/` | Optional playbook behind `netropy-lab configure` (on-link data routes) |
| `cli/` | Python CLI — validate JSON, invoke OpenTofu, print access summary |
| `config/` | JSON schema, invalid samples, and `example-kvm.json` (symlink to `test_file/example-kvm.json`) |
| `docs/` | Phase deliverables |
| `images/` | VM disk images (local only; large files gitignored) |
| `libvirt-pool/` | Local libvirt storage for the Phase 3 POC (gitignored) |
| `modules/kvm/` | OpenTofu libvirt module for the full KVM lab |
| `Netropy-VM/` | Netropy VE 5.1.3 OVA and converted qcow2 disks (local only — do not commit) |
| `poc/` | Phase 3 single-VM proof-of-concept (tool validation) |
| `project_objective/` | Original project spec and topology diagram |
| `plan/` | Intern execution workbook |
| `scripts/` | Setup verification and helper scripts |
| `test_file/` | Real `example-kvm.json` used by the CLI — do not delete |
| `AGENTS.md` | Instructions for AI assistants (Cursor/Codex) |

Full details: `docs/phase_2/repository-structure.md`

---

## Quick start (KVM)

### 1. Configure

Edit `config/example-kvm.json` (or copy it):

- Set `ssh_public_key_file` to your public key path
- Set `netropy_image` to the VE OS qcow2 (OVA disk1); disk2 is inferred as `vn-disk2-256m-5.1.3.qcow2` next to it
- Set `"provision_netropy": true` when both disks exist on this host

JSON field reference: [`docs/phase_4/json-field-contract.md`](docs/phase_4/json-field-contract.md)

### 2. Validate

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json
```

### 3. Provision the lab

**Primary (Phase 6 CLI):**

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json
PYTHONPATH=cli python3 -m netropy_lab.cli plan    -c config/example-kvm.json
PYTHONPATH=cli python3 -m netropy_lab.cli up      -c config/example-kvm.json
# wait ~90 seconds for cloud-init
```

Do **not** run with `sudo`.

**Fallback (shell scripts):**

```bash
cd modules/kvm
chmod +x run-apply.sh run-destroy.sh run-start.sh
./run-apply.sh
```

### 4. Access

```bash
ssh ubuntu@192.168.100.21   # Linux-1
ssh ubuntu@192.168.100.22   # Linux-2
ssh admin@192.168.100.10    # Netropy CLI (password not in git)
```

Web UI (on the KVM host): `http://192.168.100.10:80`  
From Windows, tunnel first: `ssh -L 8080:192.168.100.10:80 <user>@<kvm-host>` then `http://127.0.0.1:8080`

iperf3 through Netropy (Bridge mode; extra routes after boot — see `docs/phase_5/phase5-development-guide.md`):

```bash
# Linux-2: iperf3 -s
# Linux-1: iperf3 -c 192.168.102.22 -B 192.168.101.21
```

### 5. Verify the lab

After `up` and ~90 seconds for cloud-init:

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli verify -c config/example-kvm.json
```

Use `--require-forwarding` when the Netropy data path must pass (Bridge mode + routes configured per `docs/phase_5/phase5-development-guide.md`).

Details: `docs/phase_7/phase7-development-guide.md`

### 6. Destroy the lab

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli down -c config/example-kvm.json
# type 'destroy' when prompted, or add --yes
```

Fallback: `cd modules/kvm && ./run-destroy.sh`

See `docs/phase_2/security-guardrails.md` before running destroy.

**Full talk track:** [`docs/phase_9/demo-script.md`](docs/phase_9/demo-script.md)

---

## CLI

```bash
cd cli && pip install -e ".[dev]"   # optional install
# or from repo root:
PYTHONPATH=cli python3 -m netropy_lab.cli ...

netropy-lab validate -c config/example-kvm.json
netropy-lab plan    -c config/example-kvm.json
netropy-lab up      -c config/example-kvm.json
netropy-lab configure -c config/example-kvm.json   # optional Ansible: data routes
netropy-lab verify  -c config/example-kvm.json
netropy-lab down    -c config/example-kvm.json
```

Details: `docs/phase_6/phase6-development-guide.md` (provision) · `docs/phase_7/phase7-development-guide.md` (verify) · `docs/phase_7/ansible-optional-configure.md` (optional Ansible)

---

## Security

- **Never commit** secrets, `*.tfstate`, or `lab.auto.tfvars.json`
- Run `./scripts/check-secrets.sh` before each commit
- Do **not** run apply scripts with `sudo`
- Prefer environment variables over secrets in JSON (`credentials.note` is documentation only)

Details: `docs/phase_2/security-guardrails.md`

---

## Documentation

Phase deliverables under `docs/`:

| Document | Description |
|----------|-------------|
| [project_objective/](project_objective/) | Project requirements and topology (Markdown + SVG) |
| [docs/phase_1/phase1-development-guide.md](docs/phase_1/phase1-development-guide.md) | Phase 1 — development instructions |
| [docs/phase_1/phase1-architecture-note.md](docs/phase_1/phase1-architecture-note.md) | Phase 1 — architecture and networking |
| [docs/phase_2/phase2-development-guide.md](docs/phase_2/phase2-development-guide.md) | Phase 2 — development instructions |
| [docs/phase_2/setup-verification.md](docs/phase_2/setup-verification.md) | Phase 2 — dev host tool checks |
| [docs/phase_2/repository-structure.md](docs/phase_2/repository-structure.md) | Phase 2 — repo layout |
| [docs/phase_2/branch-strategy.md](docs/phase_2/branch-strategy.md) | Phase 2 — Git branch workflow |
| [docs/phase_2/security-guardrails.md](docs/phase_2/security-guardrails.md) | Phase 2 — secrets and destroy policy |
| [docs/phase_2/agents-and-cursor-rules.md](docs/phase_2/agents-and-cursor-rules.md) | Phase 2 — AI assistant rules (evidence) |
| [docs/phase_2/libvirt-vm-demo.md](docs/phase_2/libvirt-vm-demo.md) | Phase 2 — libvirt VM lifecycle demo |
| [docs/phase_3/phase3-development-guide.md](docs/phase_3/phase3-development-guide.md) | Phase 3 — development instructions |
| [docs/phase_3/phase3-tool-recommendation.md](docs/phase_3/phase3-tool-recommendation.md) | Phase 3 — tool selection and POC (workbook; called Phase 0 in project objective) |
| [docs/phase_4/phase4-development-guide.md](docs/phase_4/phase4-development-guide.md) | Phase 4 — JSON contract, schema, validate, tests |
| [docs/phase_4/json-field-contract.md](docs/phase_4/json-field-contract.md) | Phase 4 — field-by-field JSON contract |
| [docs/phase_5/phase5-development-guide.md](docs/phase_5/phase5-development-guide.md) | Phase 5 — full KVM lab, Netropy VE, iperf3 path |
| [docs/phase_6/phase6-development-guide.md](docs/phase_6/phase6-development-guide.md) | Phase 6 — CLI validate/plan/up/down |
| [docs/phase_7/phase7-development-guide.md](docs/phase_7/phase7-development-guide.md) | Phase 7 — CLI verify (health checks) |
| [docs/phase_7/ansible-optional-configure.md](docs/phase_7/ansible-optional-configure.md) | Optional Ansible — post-up data routes |
| [docs/phase_7/kvm-e2e-results.md](docs/phase_7/kvm-e2e-results.md) | KVM end-to-end acceptance test results |
| [docs/phase_7/kvm-performance-report.md](docs/phase_7/kvm-performance-report.md) | KVM performance / acceptance results |
| [docs/phase_8/kvm-to-vsphere-mapping.md](docs/phase_8/kvm-to-vsphere-mapping.md) | Phase 8 — KVM to ESXi/vSphere concept mapping |
| [docs/phase_8/esxi-setup-checklist.md](docs/phase_8/esxi-setup-checklist.md) | Phase 8 — Manual ESXi Host Client setup checklist |
| [docs/phase_8/phase8-development-guide.md](docs/phase_8/phase8-development-guide.md) | Phase 8 — ESXi POC write-up (Stage A/B complete) |
| [docs/phase_8/netplan-examples.md](docs/phase_8/netplan-examples.md) | Phase 8 — Persist Linux lab IPs (netplan) |
| [docs/phase_9/phase9-development-guide.md](docs/phase_9/phase9-development-guide.md) | Phase 9 — wrap-up guide |
| [docs/phase_9/demo-script.md](docs/phase_9/demo-script.md) | Phase 9 — live demo script |
| [docs/phase_9/handover-and-backlog.md](docs/phase_9/handover-and-backlog.md) | Phase 9 — handover + backlog |
| [docs/phase_9/known-limitations.md](docs/phase_9/known-limitations.md) | Phase 9 — versions and limits |
| [docs/phase_9/passthrough-investigation.md](docs/phase_9/passthrough-investigation.md) | Phase 9 — passthrough stretch (not implemented) |
| [docs/phase_9/problems-and-fixes.md](docs/phase_9/problems-and-fixes.md) | Phase 9 — major problems and fixes |
| [AGENTS.md](AGENTS.md) | AI assistant rules (repo — used by Cursor) |
| [plan/](plan/) | Intern execution workbook |

---

## Branch strategy

Default branch: **`main`**. Feature branches: `feature/<description>`.

See `docs/phase_2/branch-strategy.md`.

---

## License / ownership

Internal Apposite intern project — see mentor for distribution policy.
