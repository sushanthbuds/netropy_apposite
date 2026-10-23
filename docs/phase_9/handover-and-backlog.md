# Phase 9 — Handover Notes and Backlog

**Project:** Netropy VE Automated Provisioning  
**Date:** 2026-09-22  
**Primary path:** KVM automation (`modules/kvm/` + `cli/`)  
**ESXi:** Manual POC complete (`docs/phase_8/`)

---

## 1. Handover summary

A new operator should:

1. Read root [README.md](../../README.md).
2. Run `./scripts/verify-setup.sh` and `./scripts/check-secrets.sh`.
3. Use `config/example-kvm.json` with local SSH pubkey + Netropy qcow2 paths.
4. `validate` → `up` → `verify` → `down` via `PYTHONPATH=cli python3 -m netropy_lab.cli …`.
5. For data-path iperf3 through Netropy: follow `docs/phase_5/phase5-development-guide.md` (Bridge + routes).
6. For ESXi Host Client lab recreation: `docs/phase_8/esxi-setup-checklist.md`.
7. For major problems and fixes: `docs/phase_9/problems-and-fixes.md`.

AI assistants: follow [AGENTS.md](../../AGENTS.md) (no invented Netropy behavior; no secrets in git; no `sudo` apply).

---

## 2. What works today

| Capability | Status |
|------------|--------|
| JSON validate / plan / up / down (KVM) | Done |
| `verify` (KVM) | Done |
| Optional Ansible data routes (`configure`) | Done (optional) |
| Netropy VE 5.1.3 on KVM (virtio × 3, two disks) | Done |
| ESXi manual Stage A/B + Bridging + iperf3 | Done (manual) |
| OpenTofu ESXi module | Not started |
| ESXi `verify` parity | Not started |
| PCI / SR-IOV passthrough | Not implemented |

---

## 3. Secrets and operational hygiene

- Store ESXi `root` password and Netropy `admin` password in a password manager only.
- Never commit `*.tfstate`, `.terraform/`, `lab.auto.tfvars.json`, private keys, or OVAs.
- Run `./scripts/check-secrets.sh` before every commit.
- Prefer env vars over credentials in JSON.

---

## 4. Prioritized backlog (post–Phase 9)

| Priority | Item | Notes |
|----------|------|-------|
| P1 | Mentor: waive or require impairment demo (license) | Both KVM and ESXi hit Emulation OFF / license fail |
| P1 | Mentor: approve OpenTofu `modules/esxi/` | Needs template + OVA automation design; Host Client–only limits unknown |
| P2 | Optional netplan on ESXi Linux guests | `docs/phase_8/netplan-examples.md` |
| P2 | Extend CLI `verify` to ESXi when automated | KVM verify is reference |
| P3 | Passthrough stretch | Only if IOMMU + product NIC requirements confirmed — see [passthrough-investigation.md](passthrough-investigation.md) |
| P3 | CI: lint IaC + KVM smoke | Stretch from project objective |

---

## 5. Suggested mentor talking points

1. KVM is the automated Definition of Done path for a new user.
2. ESXi proved the same topology manually; automation is follow-on.
3. Passthrough left as documented non-goal for this internship wrap-up.
4. Ask: next priority — ESXi OpenTofu, license, or formal demo recording?

---

## 6. Student completion (workbook)

| Field | Value |
|-------|-------|
| Name | ____________________ |
| Date | 2026-09-22 (docs) |
| Commit/PR | ____________________ |
