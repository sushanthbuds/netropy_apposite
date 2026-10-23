# Phase 7 — Development Instructions Guide

**Project:** Netropy VE Automated Provisioning  
**Phase:** 7 — `verify` command for post-provision health checks  
**CLI package:** `cli/netropy_lab/`  
**Example JSON:** `config/example-kvm.json`

Phase 7 adds a read-only **`verify`** command that checks whether a KVM lab is healthy after `up`, without provisioning or mutating resources.

---

## 1. Purpose of Phase 7

| Goal | How `verify` helps |
|------|-------------------|
| Confirm libvirt resources exist | Networks active, VMs running, NIC counts match topology |
| Confirm guests are reachable | Ping management IPs, SSH to Linux VMs |
| Confirm cloud-init finished | `cloud-init status` on Linux guests |
| Confirm data path (optional) | Ping peer data IP through Netropy; separate summary line |
| CI / automation | `--require-forwarding` and `--bundle` for scripted runs |

`verify` does **not** configure Netropy bridging or routes. Data-path checks report **NOT READY** until you complete the manual steps in `docs/phase_5/phase5-development-guide.md`.

---

## 2. CLI usage

From the repo root:

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli verify -c config/example-kvm.json
```

| Flag | Effect |
|------|--------|
| `--require-forwarding` | Exit code `1` unless all data-path checks pass |
| `--bundle PATH` | Write JSON failure report when verify exits non-zero |

Example with strict forwarding check:

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli verify \
  -c config/example-kvm.json \
  --require-forwarding \
  --bundle /tmp/verify-fail.json
```

**Exit codes:**

| Code | Meaning |
|------|---------|
| `0` | Infrastructure OK; forwarding OK if `--require-forwarding` |
| `1` | Any `FAIL`, or forwarding not ready when `--require-forwarding` |

`NOT READY` alone does **not** fail exit code `0` (infrastructure can be up while Netropy bridging is still manual).

---

## 3. Check layers

### libvirt

- Networks `{prefix}-mgmt`, `{prefix}-data1`, `{prefix}-data2` active
- Domains from `kvm.lab_vm_names()` exist and are `running`
- NIC count from `virsh dumpxml`: Linux VMs → 2, Netropy → 3

### management

- Ping Linux and Netropy management IPs from the KVM host
- HTTP GET on Netropy mgmt (`301`/`302`/`401`/`403` count as reachable)

### linux-guest

- SSH (`BatchMode`) as `ubuntu@<mgmt_ip>`
- `cloud-init status` → `done`
- `ip -br addr` shows expected mgmt + data IPs
- `iperf3 --version` installed

### data-path

- From each Linux VM, ping the **other** VM's data IP
- `NOT READY` if Netropy is not in Bridge mode or on-link routes are missing

---

## 4. Files involved

| Path | Role |
|------|------|
| `cli/netropy_lab/verify.py` | Check implementations, report formatting, bundle writer |
| `cli/netropy_lab/kvm.py` | `run_virsh()` helper (direct + `sg libvirt` fallback) |
| `cli/netropy_lab/cli.py` | `cmd_verify`, `--require-forwarding`, `--bundle` |
| `cli/tests/test_verify.py` | Mocked unit tests for verify logic and CLI wiring |

---

## 5. Sample output

```
=== Netropy Lab Verify ===

Config: config/example-kvm.json

Layer: libvirt
  [PASS] network netropy-lab-mgmt: active
  ...

Layer: data-path
  [NOT READY] linux1 -> peer data: no reply from 192.168.102.22
           -> Set Netropy Bridge mode and add on-link data routes ...

=== Summary ===
Infrastructure:      PASS
Netropy forwarding:  NOT READY
```

---

## 6. Manual steps after infrastructure PASS

1. SSH to Netropy: `ssh admin@192.168.100.10`
2. Enable bridging on data ports (see Phase 5 guide)
3. On each Linux VM, add on-link routes for the peer data subnet if needed
4. Re-run `verify`; use `--require-forwarding` when the path test must pass

---

## 7. Tests

```bash
cd cli && PYTHONPATH=. pytest -q tests/test_verify.py tests/test_kvm.py
```

---

## 8. Phase 7 acceptance checklist

- [ ] `verify` runs from repo root without `sudo`
- [ ] libvirt / management / linux-guest checks match a running lab
- [ ] data-path reports `NOT READY` before Netropy bridge + routes
- [ ] data-path reports `PASS` after iperf3 path works (Phase 5 procedure)
- [ ] `--bundle` writes JSON on failure
- [ ] `pytest` passes in `cli/tests/`
