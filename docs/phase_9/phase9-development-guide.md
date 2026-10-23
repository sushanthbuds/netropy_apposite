# Phase 9 — Stabilize, Document, Demonstrate, and Consider Passthrough

**Project:** Netropy VE Automated Provisioning  
**Phase:** 9 — Wrap-up (workbook Phase 10)  
**Status:** **Complete** (2026-09-22)  
**Workbook:** `plan/Netropy_VE_Provisioning_Workbook_Revised.docx`  
**Related:** [demo-script.md](demo-script.md) · [handover-and-backlog.md](handover-and-backlog.md) · [known-limitations.md](known-limitations.md) · [passthrough-investigation.md](passthrough-investigation.md) · [problems-and-fixes.md](problems-and-fixes.md)

---

## 1. Purpose

Close the internship track with a **release-ready KVM path**, clear docs, a demo script, handover notes, and an explicit decision on **passthrough** (optional stretch — not implemented).

**Exit gate:** a new user can follow the root [README.md](../../README.md) to **build, verify, and destroy** the KVM lab.

---

## 2. Workbook checklist

| Item | Result |
|------|--------|
| Complete README and per-platform prerequisites | Done — README Quick start (KVM); ESXi manual in `docs/phase_8/` |
| Document JSON reference and secret handling | Done — `docs/phase_4/json-field-contract.md` + README Security |
| Document build, verify, troubleshoot, destroy | Done — README + [demo-script.md](demo-script.md) |
| Record tested versions and known limitations | Done — [known-limitations.md](known-limitations.md) |
| Run complete demo from clean starting point | Script ready — [demo-script.md](demo-script.md) (operator runs live) |
| Demonstrate idempotent re-run and clean teardown | Covered in demo script (`up` twice / `down`) |
| Create handover notes and a backlog | Done — [handover-and-backlog.md](handover-and-backlog.md) |
| Attempt passthrough only after Phase 1 stable + hardware confirmed | **Not attempted** — see [passthrough-investigation.md](passthrough-investigation.md) |
| Final presentation / live demo script | Done — [demo-script.md](demo-script.md) |

---

## 3. What “done” means for this repo

| Platform | Phase 9 expectation |
|----------|----------------------|
| **KVM** | Automated `validate` → `up` → `verify` → `down` documented and runnable |
| **ESXi** | Manual POC wrapped (`docs/phase_8/`); OpenTofu not required for Phase 9 exit |
| **Passthrough** | Investigation note only; `passthrough_data_ports` stays `false` |

---

## 4. Files delivered in Phase 9

| Path | Role |
|------|------|
| `docs/phase_9/phase9-development-guide.md` | This guide |
| `docs/phase_9/demo-script.md` | Live demo / presentation script |
| `docs/phase_9/handover-and-backlog.md` | Handover + prioritized backlog |
| `docs/phase_9/known-limitations.md` | Versions + limits |
| `docs/phase_9/passthrough-investigation.md` | Why passthrough was not built |
| `docs/phase_9/problems-and-fixes.md` | Major problems across phases and fixes |
| `README.md` | New-user build / verify / destroy path |
| `AGENTS.md` | Status row for Phase 9 |

---

## 5. Verification commands (non-destructive)

```bash
./scripts/verify-setup.sh
./scripts/check-secrets.sh
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json
```

Full lab demo (creates/destroys VMs — see [demo-script.md](demo-script.md)):

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli up     -c config/example-kvm.json
PYTHONPATH=cli python3 -m netropy_lab.cli verify -c config/example-kvm.json
PYTHONPATH=cli python3 -m netropy_lab.cli down   -c config/example-kvm.json
```

---

## 6. Verified / Assumed / Unknown / Needs Product Confirmation

### Verified

- Workbook Phase 10 checklist mapped to docs above  
- `validate` + `check-secrets.sh` PASS on this host (2026-09-22)  
- KVM path documented end-to-end in README  

### Assumed

- Mentor accepts KVM as the primary “new user” exit gate for Phase 9  
- ESXi OpenTofu remains follow-on  

### Unknown

- Whether mentor requires a live recorded demo artifact beyond the script  

### Needs Product Confirmation

- Passthrough NIC / IOMMU requirements for Netropy VE on KVM or ESXi  
- Valid license for Emulation ON / impairment demos  

**Do not commit:** passwords, `*.tfstate`, `lab.auto.tfvars.json`, OVA/qcow2 binaries.
