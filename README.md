# Netropy Lab

Automated provisioning of a **Netropy Virtual Edition (VE)** test lab from a single JSON configuration file.

**Lab topology:** 1 Netropy VE + 2 Ubuntu Linux traffic endpoints on three subnets (management, data-1, data-2).

**Target platforms:** KVM (in progress) · ESXi · AWS

---

## Status

| Component | Status |
|-----------|--------|
| Phase 0 POC (single VM) | Done — `poc/` |
| Phase 1 architecture | Done — `docs/phase_1/` |
| Phase 2 dev environment | Done — `docs/phase_2/` |
| KVM module (2 Linux VMs) | Working — `modules/kvm/` |
| Netropy VE VM | Pending image — set `provision_netropy: false` |
| Python CLI | Scaffold — `validate`, `up`, `down` |
| ESXi / AWS modules | Not started |

---

## Prerequisites

- Linux host with **KVM** and **libvirt** (`kvm-ok` passes)
- User in the **`libvirt`** group
- **OpenTofu** >= 1.6
- **Python** >= 3.10
- Ubuntu 24.04 cloud image at `images/noble-server-cloudimg-amd64.img`

See [docs/phase_2/setup-verification.md](docs/phase_2/setup-verification.md) for install commands and verified versions.

---

## Setup verification

From a fresh shell at the repo root:

```bash
chmod +x scripts/verify-setup.sh scripts/check-secrets.sh
./scripts/verify-setup.sh
```

All required checks must **PASS** before provisioning.

---

## Repository layout

| Path | Purpose |
|------|---------|
| `cli/` | Python CLI — validate JSON, invoke OpenTofu, print access summary |
| `config/` | Example JSON lab configurations |
| `docs/` | Phase deliverables and technical notes |
| `images/` | VM disk images (local only; large files gitignored) |
| `modules/kvm/` | OpenTofu libvirt module for the full KVM lab |
| `poc/` | Phase 0 single-VM proof-of-concept |
| `project_objective/` | Original project spec and topology diagram |
| `scripts/` | Setup verification and helper scripts |
| `AGENTS.md` | Instructions for AI assistants (Cursor/Codex) |

Full details: [docs/phase_2/repository-structure.md](docs/phase_2/repository-structure.md)

---

## Quick start (KVM)

### 1. Configure

Edit `config/example-kvm.json`:

- Set `ssh_public_key_file` to your public key path
- Update `netropy_image` path when the Netropy qcow2 is available
- Keep `"provision_netropy": false` until the Netropy image is ready

### 2. Validate

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json
```

### 3. Provision Linux endpoints

```bash
cd modules/kvm
chmod +x run-apply.sh run-destroy.sh run-start.sh
./run-apply.sh
# wait ~90 seconds for cloud-init
```

### 4. Access Linux VMs

```bash
ssh ubuntu@192.168.100.21   # Linux-1
ssh ubuntu@192.168.100.22   # Linux-2
iperf3 --version
```

### 5. Destroy the lab

```bash
cd modules/kvm
./run-destroy.sh
# type 'destroy' when prompted
```

See [docs/phase_2/security-guardrails.md](docs/phase_2/security-guardrails.md) before running destroy.

---

## CLI (work in progress)

```bash
cd cli
pip install -e .   # or: PYTHONPATH=cli python3 -m netropy_lab.cli ...

netropy-lab validate -c ../config/example-kvm.json
netropy-lab up -c ../config/example-kvm.json
netropy-lab down -c ../config/example-kvm.json
```

---

## Security

- **Never commit** secrets, `*.tfstate`, or `lab.auto.tfvars.json`
- Run `./scripts/check-secrets.sh` before each commit
- Do **not** run apply scripts with `sudo`

Details: [docs/phase_2/security-guardrails.md](docs/phase_2/security-guardrails.md)

---

## Documentation

| Document | Description |
|----------|-------------|
| [project_objective/](project_objective/) | Project requirements and topology |
| [docs/phase_2/branch-strategy.md](docs/phase_2/branch-strategy.md) | Git branch workflow |
| [docs/phase_2/setup-verification.md](docs/phase_2/setup-verification.md) | Dev host tool checks |
| [docs/phase_2/security-guardrails.md](docs/phase_2/security-guardrails.md) | Secrets and destroy policy |
| [AGENTS.md](AGENTS.md) | AI assistant rules |
| [plan/](plan/) | Intern execution workbook |

---

## Branch strategy

Default branch: **`main`**. Feature branches: `feature/<description>`.

See [docs/phase_2/branch-strategy.md](docs/phase_2/branch-strategy.md).

---

## License / ownership

Internal Apposite intern project — see mentor for distribution policy.
