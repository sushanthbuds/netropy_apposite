# Phase 6 — Development Instructions Guide

**Project:** Netropy VE Automated Provisioning  
**Phase:** 6 — Python CLI wraps OpenTofu for the KVM lab  
**CLI package:** `cli/netropy_lab/`  
**Example JSON:** `config/example-kvm.json`  

Phase 6 turns the Phase 5 KVM module into a **one-command workflow** from the repo root. You no longer need to `cd modules/kvm` for normal provision/destroy.

---

## 1. Purpose of Phase 6

| Before (Phase 5) | After (Phase 6) |
|------------------|-----------------|
| `./modules/kvm/run-apply.sh` | `netropy-lab up -c config/example-kvm.json` |
| `./modules/kvm/run-destroy.sh` | `netropy-lab down -c config/example-kvm.json` |
| Manual `tofu plan` in `modules/kvm/` | `netropy-lab plan -c config/example-kvm.json` |

Phase 6 does **not** add `verify` (Phase 7) or an ESXi module.

---

## 2. CLI commands

Run from the repo root (or install with `pip install -e cli/`):

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json
PYTHONPATH=cli python3 -m netropy_lab.cli plan    -c config/example-kvm.json
PYTHONPATH=cli python3 -m netropy_lab.cli up      -c config/example-kvm.json
PYTHONPATH=cli python3 -m netropy_lab.cli down    -c config/example-kvm.json
```

| Command | Provisions? | OpenTofu? |
|---------|-------------|-----------|
| `validate` | No | No |
| `plan` | No | Yes (`tofu plan` only) |
| `up` | Yes | Yes (`tofu apply`) |
| `down` | Yes (destroy) | Yes (`tofu destroy`) |

**Do not run with `sudo`.** The CLI uses `sg libvirt` internally.

---

## 3. Files involved in Phase 6

| Path | Role |
|------|------|
| `cli/netropy_lab/cli.py` | Commands: `validate`, `plan`, `up`, `down` |
| `cli/netropy_lab/tfvars.py` | Builds `lab.auto.tfvars.json` (shared with `run-apply.sh`) |
| `cli/netropy_lab/kvm.py` | libvirt checks, `sg libvirt` OpenTofu, post-apply VM start |
| `cli/netropy_lab/validator.py` | JSON schema + semantics (Phase 4) |
| `cli/tests/test_tfvars.py` | Tfvars unit tests |
| `cli/tests/test_kvm.py` | KVM helper unit tests |
| `cli/tests/test_cli_commands.py` | Command flow tests (mocked) |
| `modules/kvm/run-apply.sh` | Fallback; calls same tfvars Python module |
| `modules/kvm/run-destroy.sh` | Fallback destroy script |

---

## 4. What `up` does (step by step)

1. **Validate** JSON (`validate_config`).
2. **Write tfvars** to `modules/kvm/lab.auto.tfvars.json`:
   - `netropy_config_image` inferred from disk2 sibling of `netropy_image`
   - `ubuntu_image` → `/var/lib/netropy-lab-images/noble-server-cloudimg-amd64.img`
3. **Preflight (KVM):** not root, user in `libvirt` group, create pool dir.
4. **OpenTofu:** `sg libvirt -c "tofu init -upgrade && tofu apply -auto-approve"`.
5. **Post-apply (KVM):**
   - Best-effort sudo pool permission fix
   - Autostart/start `netropy-lab-linux1`, `netropy-lab-linux2`, `netropy-lab-netropy`
6. **Print access summary** (SSH, web UI, iperf3 hint).

---

## 5. What `down` does

1. Validate JSON (and write tfvars if missing).
2. **Confirm destroy:** type `destroy`, or pass `--yes`, or set `NETROPY_LAB_CONFIRM_DESTROY=yes`.
3. `sg libvirt -c "tofu destroy -auto-approve"`.

See `docs/phase_2/security-guardrails.md` before destroying.

---

## 6. Prerequisites

Same as Phase 5:

- User in **`libvirt`** group (log out/in after `usermod`)
- OpenTofu >= 1.6
- Ubuntu cloud image at `/var/lib/netropy-lab-images/noble-server-cloudimg-amd64.img`
- Netropy OVA disks under `Netropy-VM/` when `provision_netropy: true`

```bash
./scripts/verify-setup.sh
```

---

## 7. Unit tests

```bash
cd cli
PYTHONPATH=. pytest -q
```

Expected: all tests pass (validator + tfvars + kvm + cli commands).

---

## 8. Manual verification (exit criteria)

- [ ] `validate` passes on `config/example-kvm.json`
- [ ] `plan` shows OpenTofu plan without error (libvirt group active)
- [ ] `up` creates/updates the three-VM lab (or reports no changes if already applied)
- [ ] Linux mgmt IPs ping; Netropy mgmt ping/HTTP work
- [ ] `down` with confirmation removes the lab (or use `--yes` in automation)

Compare outcome with Phase 5 `./run-apply.sh` — same tfvars builder, same OpenTofu module.

---

## 9. Explain Phase 6 in your own words (student self-check)

Phase 6 wrapped the working KVM lab in a Python CLI. One JSON file drives validate, plan, up, and down. The CLI writes the same tfvars the shell script used, runs OpenTofu under `sg libvirt`, starts the VMs after apply, and prints how to SSH in. Destroy requires typing `destroy` so the lab is not removed by accident.

---

## 10. What comes next

- **Phase 7** — `verify` command (ping expected IPs, optional iperf3 check)
- ESXi platform module (not started)

---

## 11. Verified / Assumed / Unknown / Needs Product Confirmation

### Verified

- Shared tfvars module matches `run-apply.sh` (disk2 inference, host ubuntu path).
- `up`/`down`/`plan` use `sg libvirt` and libvirt group checks.
- 32 unit tests pass in `cli/tests/`.

### Assumed

- `./run-apply.sh` remains a supported fallback for mentors who prefer shell scripts.
- Host Ubuntu image stays at `/var/lib/netropy-lab-images/`.

### Unknown

- Whether CI will run KVM integration tests (unit tests mock OpenTofu/virsh today).

### Needs Product Confirmation

- None for Phase 6 scope (CLI plumbing only).

---

**Document status:** Development instructions for Phase 6 (intern reference).  
**Do not commit:** secrets, private keys, `*.tfstate`, or `lab.auto.tfvars.json`.
