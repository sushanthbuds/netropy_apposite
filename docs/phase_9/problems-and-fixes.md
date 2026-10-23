# Problems Encountered and How They Were Solved

**Project:** Netropy VE Automated Provisioning  
**Purpose:** Mentor / handover reference — major blockers across Phases 3–9  
**Date:** 2026-09-22  
**Related:** `docs/phase_5/phase5-development-guide.md`, `docs/phase_8/phase8-development-guide.md`, `docs/phase_9/known-limitations.md`  
**Evidence images (debug only):** `live-panic.png`, `modules/kvm/netropy-console.png` — not Phase 7 E2E PASS evidence

---

## Summary table

| # | Problem | Platform | Fix |
|---|---------|----------|-----|
| 1 | Kernel panic — deadlocked on memory (`live-panic`) | KVM | 8 GiB RAM + correct Netropy boot settings |
| 2 | `<<no data ports>>` | KVM | `cpu mode=host-passthrough` + virtio × 3 (mgmt→data1→data2) |
| 3 | `<<system error>>` / missing `/config` | KVM | Both OVA disks on SATA (OS `sda`, config `sdb`) |
| 4 | QEMU cannot read disks after apply/destroy | KVM | Fix pool ownership; never `sudo` apply |
| 5 | License / Emulation OFF | KVM + ESXi | Path test with Bridging + emulation off (mentor accepted) |
| 6 | Lab up but data path / iperf3 fails | KVM | Netropy Bridging + on-link routes on Linux guests |
| 7 | Unreachable hosts / wrong IPs | ESXi | Map `ens*` from Edit settings → port group (do not assume NIC order) |
| 8 | Bridging path dead after Netropy cutover | ESXi | Promiscuous / MAC changes / Forged transmits = Accept |
| 9 | Netropy on ZeroConf `169.254.x.x` | ESXi | `mgmt set addr 192.168.100.10 netmask 255.255.255.0` |
| 10 | ESXi hostname / VPN access friction | ESXi | Host Client by IP over company VPN |

---

## 1. Kernel panic / `live-panic` (KVM)

**Symptom:** Console showed Linux kernel panic. Last line typically:

`Kernel panic - not syncing: System is deadlocked on memory`

Libvirt still listed the domain as running. Ping/SSH/UI to `192.168.100.10` failed (no guest stack).

**Cause:** Guest under-resourced / unhealthy boot (early lab used ~4 GiB); panic before networking came up.

**Fix:**

- Set Netropy memory to **8 GiB** in the KVM module
- Keep the known-good boot recipe (two disks, virtio NICs, host-passthrough — see below)

**Note:** `live-panic.png` is an **old debugging screenshot**. The Phase 7 E2E run that **PASSED** did not produce this panic; do not embed it as E2E failure evidence.

---

## 2. `<<no data ports>>` (KVM)

**Symptom:** Netropy CLI / status showed no data ports (or equivalent `<<no data ports>>`).

**Cause:** Default QEMU CPU model (`qemu64`) lacked required host ISA flags for this VE image on the PowerEdge host.

**Fix:**

- `cpu mode=host-passthrough`
- Three **virtio** NICs in order: management → data-1 → data-2
- Confirm with `engine 1 show` → Port 1 / Port 2 up

---

## 3. `<<system error>>` / missing `/config` (KVM)

**Symptom:** Appliance system error; `/config` missing or incomplete.

**Cause:** Only the OS disk (OVA disk1) was attached.

**Fix:** Attach **both** OVA-derived disks on SATA:

- `sda` — OS (`vn-disk1g-5.1.3.qcow2`)
- `sdb` — config (`vn-disk2-256m-5.1.3.qcow2`)

CLI infers disk2 as sibling of disk1 when provisioning Netropy.

---

## 4. Disk / pool permission errors (KVM)

**Symptom:** Cold `up` or post-destroy apply fails; QEMU cannot read volumes under the lab pool.

**Cause:** Volume ownership not readable by `libvirt-qemu` after create/destroy; applying as root breaks `$HOME` / SSH key paths.

**Fix:**

- Run apply/CLI as normal user (`sg libvirt`), **never** `sudo` for the whole apply
- Fix ownership: `chown libvirt-qemu:libvirt` and `chmod 660` on pool disks, or `scripts/fix-libvirt-permissions.sh`
- Retry `up`

---

## 5. License Validation Failed / Emulation OFF

**Symptom:** Impairment / shaping demo not available; Emulation often OFF.

**Cause:** Lab license state on the VE image.

**Fix (process, not product):** Mentor accepted **path-only** proof — Bridging + iperf3 with emulation off. Full impairment remains **Needs Product Confirmation**.

---

## 6. Automation up, data path still fails (KVM)

**Symptom:** VMs running and mgmt SSH works; Linux-1 ↔ Linux-2 data ping/iperf3 fails; `verify` data-path NOT READY.

**Cause:** Provisioning does not configure Netropy Bridge or guest on-link routes to the peer data subnet.

**Fix:**

- Netropy UI: Bridge/Route → **Bridging**
- On Linux guests: on-link routes (Phase 5 procedure) or optional `configure` (Ansible)
- Then `verify --require-forwarding` and/or iperf3 bind to data IPs

---

## 7. Wrong NIC ↔ port-group mapping (ESXi)

**Symptom:** Wrong IPs on interfaces; ARP failures; “unreachable” peers.

**Cause:** Assumed “NIC 1 = mgmt.” ESXi adapter order defines `ens160`, `ens192`, … differently.

**Fix:** From **Edit settings**, map each adapter to its port group (`sushanth-mgmt` / `data1` / `data2`), then assign IPs to the matching `ens*`.

---

## 8. ESXi Bridging path dead until security Accept

**Symptom:** After Netropy Bridging cutover, ping/iperf3 through Netropy failed.

**Cause:** Port group / vSwitch security blocked frames needed for Bridging.

**Fix:** On data networks (and/or their vSwitches), set to **Accept**:

- Promiscuous mode  
- MAC address changes  
- Forged transmits  

Then retest ping and iperf3 (~3.85 Gbit/s verified on this lab).

---

## 9. Netropy management on ZeroConf (ESXi)

**Symptom:** Mgmt address `169.254.x.x`; UI/SSH on `192.168.100.10` failed until fixed.

**Cause:** Isolated mgmt port group with no DHCP.

**Fix:**

```text
mgmt set addr 192.168.100.10 netmask 255.255.255.0
```

Access UI via SSH tunnel from a reachable jump host/VM when needed; keep the tunnel open.

---

## 10. ESXi hostname / VPN access

**Symptom:** Hostname did not resolve; browser/MFA friction on VPN.

**Fix:** Connect company VPN; open Host Client by **IP** (lab: `https://192.168.144.43/ui`). Store `root` password outside git.

---

## Still open (not solved in this internship)

| Item | Status |
|------|--------|
| OpenTofu `modules/esxi/` + CLI `platform: esxi` | Follow-on (mentor approve) |
| ESXi `verify` | Not started |
| Emulation ON / impairment demo | Needs Product Confirmation / license |
| PCI / SR-IOV passthrough | Stretch — investigated, not implemented (`docs/phase_9/passthrough-investigation.md`) |
| Persistent ESXi guest IPs | Optional netplan (`docs/phase_8/netplan-examples.md`) |

---

## Verified / Assumed / Unknown / Needs Product Confirmation

### Verified

- Panic, no-data-ports, missing-disk2, pool perms, ESXi NIC mapping, security Accept, and static mgmt were real blockers and were resolved as above on this lab.
- Path tests with Bridging + emulation off succeeded on KVM and ESXi.

### Assumed

- Mentor continues to accept path-only checks when license blocks Emulation ON.

### Unknown

- Exact product minimum RAM/vCPU for VE 5.1.3 (lab-proven: 8 GiB + host-passthrough on this host).

### Needs Product Confirmation

- Official license for Emulation ON  
- Official ESXi NIC model / order for OVA  
- Passthrough / SR-IOV support matrix  

**Do not commit:** passwords, `*.tfstate`, or VE image binaries.
