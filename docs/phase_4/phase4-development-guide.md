# Phase 4 — Development Instructions Guide

**Project:** Netropy VE Automated Provisioning  
**Phase:** 4 — Define the JSON Configuration Contract  
**Related write-up:** `docs/phase_4/json-field-contract.md`  
**Schema file:** `config/lab-config.schema.json`  
**Example config:** `config/example-kvm.json`  
**CLI package:** `cli/netropy_lab/`  

---

## 1. Purpose of Phase 4

Phase 4 defines the **single JSON file** that describes a lab, then proves that **invalid input fails early** and **valid input is summarized** — without creating any VMs.

You must be able to:

1. **Name every field** — required vs optional, types, and meaning  
2. **Reject bad JSON** — schema errors at a precise field  
3. **Reject bad meaning** — IP not in subnet, duplicates, overlapping CIDRs, missing files  
4. **Normalize valid JSON** — typed Python models + a human-readable summary  
5. **Prove it with tests** — unit tests for each validation rule  

**Exit gate (workbook):** Invalid input fails with a precise field-level message; valid input produces a normalized summary. Validation **never provisions**.

Phase 4 does **not** stand up the three-VM KVM lab or finish the full CLI (`up`/`down`/`verify`). Those are later phases.

---

## 2. Phase 4 deliverables (workbook tasks)

| Task | Deliverable | Location |
|------|-------------|----------|
| 4-1 | Required and optional JSON fields | `docs/phase_4/json-field-contract.md` |
| 4-2 | JSON Schema | `config/lab-config.schema.json` |
| 4-3 | Typed Python models | `cli/netropy_lab/models.py` |
| 4-4 | Semantic validation | `cli/netropy_lab/validator.py` |
| 4-5 | Valid and invalid samples | `config/example-kvm.json`, `config/invalid/` |
| 4-6 | Unit tests | `cli/tests/test_validator.py` |
| 4-7 | `validate` prints a summary; no OpenTofu | `cli/netropy_lab/cli.py` (`cmd_validate`) |

---

## 3. Files involved in Phase 4

| Path | Role |
|------|------|
| `docs/phase_4/json-field-contract.md` | Field-by-field contract (what each JSON key means) |
| `docs/phase_4/phase4-development-guide.md` | This guide |
| `config/lab-config.schema.json` | JSON Schema Draft 2020-12 (structure and types) |
| `config/example-kvm.json` | Valid KVM reference config |
| `config/invalid/` | Intentionally broken samples for tests and demos |
| `cli/netropy_lab/models.py` | Frozen dataclasses (`LabConfig`, subnets, instances, options) |
| `cli/netropy_lab/validator.py` | Syntax + schema + semantic checks |
| `cli/netropy_lab/cli.py` | `validate` command (and later `up`/`down` scaffold) |
| `cli/tests/test_validator.py` | Unit tests for validation rules |
| `cli/pyproject.toml` | Package metadata; depends on `jsonschema` |

---

## 4. Why a contract before the full lab

The intern project is **JSON in → lab out**. If the JSON is wrong, you want a **clear error in seconds**, not a half-created libvirt domain an hour later.

| Layer | Catches | Example |
|-------|---------|---------|
| JSON syntax | Broken file | missing comma |
| JSON Schema | Wrong shape | missing `platform`, CIDR not a string |
| Python semantics | Wrong meaning | `192.168.101.21` placed in the mgmt subnet |
| Typed model | Normalized defaults | `naming_prefix` defaults to `netropy-lab` |

`validate` runs the first three layers, then prints the model as a **normalized summary**. It must **not** call OpenTofu.

---

## 5. What the JSON describes

The file is the lab’s source of truth for **platform, images, subnets, and instance IPs**.

### Three VMs (IPs in JSON even if Netropy is skipped)

| Instance | Fields | Subnets |
|----------|--------|---------|
| Netropy VE | `mgmt_ip`, `data1_ip`, `data2_ip` | mgmt, data1, data2 |
| Linux-1 | `mgmt_ip`, `data_ip` | mgmt, data1 |
| Linux-2 | `mgmt_ip`, `data_ip` | mgmt, data2 |

### Three subnets

| Key | Role |
|-----|------|
| `subnets.mgmt.cidr` | SSH / Netropy management |
| `subnets.data1.cidr` | Linux-1 data ↔ Netropy data port 1 |
| `subnets.data2.cidr` | Netropy data port 2 ↔ Linux-2 data |

Full field table: `docs/phase_4/json-field-contract.md`.

**Gating Netropy:** set `"options": { "provision_netropy": false }` until a real VE image exists. Schema still requires Netropy **IP fields** (the topology is fixed); the image path is only required when provisioning is enabled.

---

## 6. Prerequisites

From a normal user shell (not root), at the repo root:

```bash
python3 --version    # 3.10 or newer
```

Install the CLI and test extras:

```bash
cd ~/netropy-lab/cli
pip install -e ".[dev]"
```

**Why:** Schema validation needs the `jsonschema` package. Tests need `pytest`.

If you do not want a venv install, you can still run:

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json
```

…but `jsonschema` must already be importable.

---

## 7. Validation layers (how they work)

### 7.1 JSON syntax

`json.load` in `validator.py`.

**Why:** A parse error is cheaper than schema iteration.  
**How:** A missing comma fails with `Invalid JSON in …`.

### 7.2 JSON Schema (structure)

`config/lab-config.schema.json` via `Draft202012Validator`.

**Why:** Required keys, enums (`platform`: kvm / esxi), CIDR-like strings, nested objects.  
**How:** The first schema error is formatted as `Schema validation failed at <path>: <message>` so you know **which field** broke.

### 7.3 Semantic rules (Python)

Still in `validator.py`, after schema success:

| Check | Rule |
|-------|------|
| Platform | Must be `kvm` or `esxi` |
| SSH key | `ssh_public_key_file` exists and is a file (public key only) |
| CIDRs | Valid IPv4 networks; the three subnets must not overlap |
| IP membership | Each instance IP sits in the matching subnet |
| Unique IPs | All seven instance addresses are distinct |
| Sizing | `vcpu` 1–64; `memory_mb` 512–131072 |
| Netropy image | Required **and** must exist on disk when `provision_netropy` is true (KVM) |

**Why `ipaddress`:** CIDR and “IP in subnet” are easy to get wrong with string prefix checks.

### 7.4 Typed models

`lab_config_from_dict` builds frozen dataclasses (`LabConfig`, `SubnetsConfig`, …).

**Why:** Later CLI/OpenTofu code can take a typed object instead of a loosely keyed dict. Defaults (prefix, options) are applied here.

---

## 8. Step-by-step: run and understand Phase 4

### 8.1 Validate a good config

```bash
cd ~/netropy-lab
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json
```

**Why:** This is the workbook exit path for *valid* input.  
**Expected:** `Config OK: …` followed by a block titled `=== Normalized lab configuration ===` listing platform, subnets, instance IPs, and options. **No** OpenTofu init/apply.

If `ssh_public_key_file` points at a missing key, fix the path in the JSON (or create a public key). That is a semantic failure, not a schema failure.

### 8.2 Fail an invalid sample (field-level error)

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/invalid/missing-platform.json
echo $?    # non-zero
```

**Why:** Workbook exit path for *invalid* input.  
**Expected:** `Config error: …` mentioning `platform` (or the field that sample breaks). Process exit status is not 0.

Try the other files in `config/invalid/` the same way.

### 8.3 Run the unit tests

```bash
cd ~/netropy-lab/cli
pytest -q
```

**Why:** Tests must cover the validation rules, not only the happy path.  
**Expected:** All tests pass (validator tests plus any other CLI tests in that folder).

Tests build a temporary JSON and a fake public-key file so they do not depend on your real `~/.ssh` key.

### 8.4 Confirm validate does not provision

Read `cmd_validate` in `cli/netropy_lab/cli.py`: it only calls `validate_config` and prints the summary.

`cmd_up` / `cmd_down` exist as later-phase scaffold. **Do not** treat `up` as a Phase 4 acceptance test.

---

## 9. Invalid samples (`config/invalid/`)

| File | What it proves |
|------|----------------|
| `missing-platform.json` | Schema: required `platform` |
| `bad-cidr.json` | Schema / CIDR pattern |
| `ip-outside-subnet.json` | Semantic: IP not in its subnet |
| `duplicate-ips.json` | Semantic: same address used twice |
| `overlapping-subnets.json` | Semantic: overlapping CIDRs |
| `bad-vcpu.json` | Schema / vCPU bounds |

**How to use them:** keep them in git as fixtures. Do not “fix” them to be valid.

---

## 10. Secrets and safety (Phase 4)

- JSON may list a **path** to an SSH **public** key. Never put private keys or passwords in the file.  
- `credentials` is a human note only (see field contract).  
- `validate` must not print private key material. The normalized summary prints the public-key **path**, not key contents.  
- Do not commit `lab.auto.tfvars.json`, `*.tfstate`, or real credentials.

---

## 11. How Phase 4 connects to later work

```text
Phase 4 (JSON contract + validate)
    →  modules/kvm/ reads the same fields via generated tfvars (Phase 5 apply)
    →  Phase 6 CLI: plan/create/destroy wrap OpenTofu using this contract
    →  Phase 7 verify: expected IPs come from the same JSON
```

| Phase 4 output | Used later |
|----------------|------------|
| Field contract + schema | Stable input for KVM / ESXi modules |
| Semantic IP rules | Prevents wiring Linux-1 data onto the wrong subnet |
| `provision_netropy` | Lets Phase 5 ship Linux-only until the VE image exists |
| Unit tests | Regression net when CLI commands grow |

---

## 12. Key lessons learned in Phase 4

1. **Schema ≠ semantics** — a valid-looking IPv4 string can still sit in the wrong subnet.  
2. **Fail at a field path** — `instances.linux1.data_ip` is more useful than “invalid config”.  
3. **Defaults belong in the model** — missing `naming_prefix` should still produce a complete summary.  
4. **Validation must be side-effect free** — no `tofu apply` from `validate`.  
5. **Netropy image is conditional** — topology IPs stay in JSON; the disk file is only required when you actually provision VE.

---

## 13. Phase 4 exit criteria (self-check)

You can mark Phase 4 complete when:

- [ ] Field contract is written (`json-field-contract.md`)
- [ ] JSON Schema exists and is used by the validator
- [ ] Typed models load a valid file after schema + semantic checks
- [ ] Invalid samples fail with a precise field-level message
- [ ] Unit tests cover required schema and semantic rules
- [ ] `validate` prints a normalized summary and does not invoke OpenTofu
- [ ] You can explain this phase in your own words (see below)

---

## 14. Explain Phase 4 in your own words (student self-check)

Phase 4 locked down the lab JSON: what fields are required, how they are typed, and which extra rules (IPs in the right subnets, no duplicates, no overlapping networks, SSH key path, optional Netropy image) must pass. The `validate` command runs those checks and prints a clean summary. It never creates VMs. That gives a safe front door before the full KVM lab and later CLI commands.

---

## 15. What comes next

- **Phase 5** — Done. Full KVM lab write-up: `docs/phase_5/phase5-development-guide.md`.  
- **Phase 6** — Thicker CLI around the tested KVM module (`plan` / create / destroy without calling OpenTofu by hand).

---

## 16. Quick command cheat sheet

```bash
# Install CLI + tests
cd ~/netropy-lab/cli
pip install -e ".[dev]"

# Unit tests
pytest -q

# Valid config (no provisioning)
cd ~/netropy-lab
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json

# Invalid samples (expect Config error)
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/invalid/missing-platform.json
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/invalid/ip-outside-subnet.json
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/invalid/duplicate-ips.json
```

---

## 17. Verified / Assumed / Unknown / Needs Product Confirmation

### Verified

- Typed `LabConfig` models load from valid JSON after schema + semantic checks.  
- `validate` prints a normalized summary and does not invoke OpenTofu.  
- Invalid fixtures under `config/invalid/` fail with field-oriented errors.  
- Unit tests in `cli/tests/test_validator.py` cover the Phase 4 rules above.

### Assumed

- `jsonschema` is installed in the environment used to run `validate` (`pip install -e .` from `cli/`).  
- Example KVM JSON used `provision_netropy: false` until the VE image existed; Phase 5 on this host uses `true` (see `docs/phase_5/`).

### Unknown

- Whether a mentor prefers Pydantic instead of stdlib dataclasses (dataclasses are what the code uses).

### Needs Product Confirmation

- Netropy VE image format, boot mode, NIC model, and management URL are **not** defined by Phase 4. The JSON only stores paths and IPs. Product answers belong in Phase 5.

---

**Document status:** Development instructions for Phase 4 (intern reference).  
**Do not commit:** secrets, private keys, `*.tfstate`, or `lab.auto.tfvars.json`.
