# Phase 9 — Passthrough Investigation (Stretch — Not Implemented)

**Status:** Documented only — **not built**  
**JSON flag:** `options.passthrough_data_ports` remains `false`  
**Workbook rule:** Attempt passthrough only after Phase 1 is stable **and** hardware support is confirmed.

---

## 1. What the project asks for

From `project_objective/Netropy-VE-Provisioning-Intern-Project.md` (objective “Phase 2” / workbook Phase 10 stretch):

- Netropy **data ports** in PCI passthrough / SR-IOV / DirectPath (platform-dependent)
- Linux endpoints join those ports via an **external** mechanism (typically a **host Linux bridge**)
- Same iperf3 acceptance as the emulated-NIC lab

KVM today uses **emulated virtio NICs** plus `cpu mode=host-passthrough` so the guest CPU exposes needed ISA flags. That is **not** the same as PCI device passthrough of Netropy data NICs.

---

## 2. Why this internship did not implement it

| Gate | Result |
|------|--------|
| Emulated-NIC lab stable on KVM | Met (Phases 5–7) |
| Hardware IOMMU / SR-IOV inventory confirmed for Netropy data path | **Not confirmed** with product/mentor for this wrap-up |
| Product NIC / passthrough requirements for VE 5.1.3 | **Needs Product Confirmation** |
| ESXi DirectPath / SR-IOV lab access | Not pursued after Host Client Bridging POC |

Implementing passthrough without those answers would invent Netropy behavior — forbidden by `AGENTS.md`.

---

## 3. Topics to document if later attempted

Operators must research and record (no values invented here):

| Topic | Why it matters |
|-------|----------------|
| IOMMU enabled in BIOS/UEFI | Required for VFIO / device assignment |
| VFIO / `vfio-pci` binding | KVM passthrough ownership of PF/VF |
| SR-IOV VF count and driver | Split physical NIC into VFs |
| Device ownership vs libvirt | Who binds the device before OpenTofu |
| Host Linux bridge design | External join of Linux VM NIC ↔ Netropy VF |
| ESXi DirectPath I/O / SR-IOV | Different inventory and security model |

---

## 4. Recommended next step (if mentor wants the stretch)

1. Confirm host: `dmesg` / kernel IOMMU messages; NIC SR-IOV capability (**ops**, not guessed here).
2. Get Netropy product confirmation: required NIC model, which ports can be passed through, guest driver expectations.
3. Design OpenTofu/libvirt changes behind `passthrough_data_ports: true` without changing default JSON examples.
4. Keep default path (`false`) green on every regression.

---

## Verified / Assumed / Unknown / Needs Product Confirmation

### Verified

- Flag exists in schema and examples as `false`
- Workbook treats passthrough as optional after stable Phase 1

### Assumed

- Mentor accepts “investigated, not implemented” for Phase 9 closeout

### Unknown

- Whether this PowerEdge host’s NICs and IOMMU layout support the Netropy data-port design

### Needs Product Confirmation

- Official passthrough / SR-IOV support for Netropy VE 5.1.3 on KVM and ESXi
