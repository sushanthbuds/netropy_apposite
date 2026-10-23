# Phase 4 — JSON Field Contract

**Project:** Netropy VE Automated Provisioning  
**Phase:** 4 — Define the JSON Configuration Contract  
**Schema file:** `config/lab-config.schema.json`  
**Example config:** `config/example-kvm.json`  

---

## Purpose

This document defines every field in the lab JSON configuration: what is required, what is optional, and how semantic rules (IP placement, file paths) are validated.

JSON Schema checks **structure and types**. Python validation in `cli/netropy_lab/validator.py` checks **semantics** (IP in subnet, duplicate IPs, overlapping subnets — expanded in Phase 4 Day 2).

---

## Top-level fields

| Field | Required? | Type | Description |
|-------|-----------|------|-------------|
| `platform` | **Yes** | `"kvm"` \| `"esxi"` | Target hypervisor |
| `ubuntu_lts_version` | **Yes** | string | Ubuntu LTS for Linux endpoints (e.g. `"24.04"`) |
| `ssh_public_key_file` | **Yes** | string (path) | Path to SSH **public** key on provisioning host |
| `subnets` | **Yes** | object | Management and two data subnet CIDRs |
| `instances` | **Yes** | object | Static IPs for Netropy and both Linux VMs |
| `netropy_image` | Conditional | string | Required when `options.provision_netropy` is `true`. **KVM:** local qcow2 path. |
| `naming_prefix` | Optional | string | VM/resource name prefix (default: `netropy-lab`) |
| `options` | Optional | object | Sizing flags and feature toggles |
| `credentials` | Optional | object | Placeholder notes only — **never real secrets** |

---

## `subnets`

All three keys are required.

| Field | Required? | Type | Description |
|-------|-----------|------|-------------|
| `subnets.mgmt.cidr` | **Yes** | CIDR string | Management network (SSH, Netropy UI) |
| `subnets.data1.cidr` | **Yes** | CIDR string | Data network 1 (Linux-1 ↔ Netropy data port 1) |
| `subnets.data2.cidr` | **Yes** | CIDR string | Data network 2 (Netropy data port 2 ↔ Linux-2) |

Subnets must not overlap (semantic validation in Python).

---

## `instances`

### Netropy VE

| Field | Required? | Must be in subnet |
|-------|-----------|-------------------|
| `instances.netropy.mgmt_ip` | **Yes** | `subnets.mgmt` |
| `instances.netropy.data1_ip` | **Yes** | `subnets.data1` |
| `instances.netropy.data2_ip` | **Yes** | `subnets.data2` |

### Linux-1

| Field | Required? | Must be in subnet |
|-------|-----------|-------------------|
| `instances.linux1.mgmt_ip` | **Yes** | `subnets.mgmt` |
| `instances.linux1.data_ip` | **Yes** | `subnets.data1` |

### Linux-2

| Field | Required? | Must be in subnet |
|-------|-----------|-------------------|
| `instances.linux2.mgmt_ip` | **Yes** | `subnets.mgmt` |
| `instances.linux2.data_ip` | **Yes** | `subnets.data2` |

All instance IPs must be unique (semantic validation in Python).

---

## `options`

| Field | Required? | Type | Default | Description |
|-------|-----------|------|---------|-------------|
| `options.provision_netropy` | Optional | boolean | `true` | When `false`, skip Netropy VM (no image needed yet) |
| `options.passthrough_data_ports` | Optional | boolean | `false` | Stretch goal — PCI passthrough data ports |
| `options.vcpu` | Optional | integer | module default | vCPUs per VM (1–64) |
| `options.memory_mb` | Optional | integer | module default | RAM in MiB (512–131072) |

---

## `credentials`

| Field | Required? | Description |
|-------|-----------|-------------|
| `credentials.note` | Optional | Human-readable hint only |

**Rules:**

- KVM: local libvirt socket — no remote credentials in JSON.
- ESXi: use env vars or an untracked local secrets file.

---

## Validation layers

| Layer | Tool | Checks |
|-------|------|--------|
| Syntax | `json.load` | Valid JSON |
| Structure | `config/lab-config.schema.json` | Required keys, types, enums |
| Semantics | `cli/netropy_lab/validator.py` | IP in subnet, paths exist, duplicates, overlap |

The `validate` command runs all three layers and prints a **normalized summary**. It never calls OpenTofu or provisions VMs.

---

## Example (KVM)

See `config/example-kvm.json`. Invalid examples live under `config/invalid/`.

---

## Related files

| Path | Role |
|------|------|
| `docs/phase_4/phase4-development-guide.md` | Intern development instructions |
| `config/lab-config.schema.json` | JSON Schema (Draft 2020-12) |
| `config/example-kvm.json` | Valid KVM reference configuration |
| `config/invalid/` | Intentionally invalid samples |
| `cli/netropy_lab/models.py` | Typed dataclasses (`LabConfig`, …) |
| `cli/netropy_lab/validator.py` | Schema + semantic validation |
| `cli/tests/test_validator.py` | Unit tests |
| `project_objective/Netropy-VE-Provisioning-Intern-Project.md` | Source requirements (§7.1) |

---

**Status:** Phase 4 Days 1–3 complete  
**Next:** Phase 6 — CLI `up`/`down` around the tested KVM module (`docs/phase_5/` is the lab write-up)
