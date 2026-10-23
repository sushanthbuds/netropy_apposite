# Phase 8 — Development Instructions Guide

**Project:** Netropy VE Automated Provisioning  
**Phase:** 8 — ESXi Host Client lab (manual POC complete)  
**Status:** **Wrapped up (manual Phase 8 complete)** — OpenTofu `modules/esxi/` / ESXi CLI / impairment are follow-on  
**Checklist:** [esxi-setup-checklist.md](esxi-setup-checklist.md)  
**Mapping:** [kvm-to-vsphere-mapping.md](kvm-to-vsphere-mapping.md)  
**Date completed (intern lab):** 2026-09-21  

---

## 1. Purpose

Prove the same lab recipe on **standalone ESXi** (not vCenter):

**Linux-1 data → Netropy Port 1 → Netropy Port 2 → Linux-2 data**

Mentor order: Linux bridge POC first, then swap middle box for Netropy **OVA**. OpenTofu ESXi module comes **after** this manual path works.

---

## 2. What was delivered

| Deliverable | Result |
|-------------|--------|
| KVM→ESXi mapping | `kvm-to-vsphere-mapping.md` |
| Access | Host Client via IP; user `root` (password not in git) |
| Networks | Intern-owned vSwitches + port groups `sushanth-mgmt`, `sushanth-data1`, `sushanth-data2` |
| Stage A | 3 Ubuntu VMs; Linux bridge; ping + iperf3 through bridge |
| Stage B | Netropy VE from OVA; Bridging; ping + iperf3 ~3.85 Gbit/s through Netropy |
| Docs | This guide + updated checklist |

**Not delivered (explicit follow-on):** `modules/esxi/`, `config/example-esxi.json`, CLI `platform: esxi`, ESXi `verify`.

---

## 3. Lab inventory (no secrets)

| Item | Value |
|------|--------|
| ESXi UI | `https://192.168.144.43/ui` (hostname may not resolve) |
| Datastore | `esxi-alab2-disk` |
| Linux ISO | `iso/ubuntu-24.04.4-desktop-amd64.iso` |
| Netropy image | OVA `vn-disk1g-5.1.3` (from mentor shared link; not in git) |
| Port groups | `sushanth-mgmt`, `sushanth-data1`, `sushanth-data2` |
| VMs | `sushanth-linux1`, `sushanth-linux2`, `sushanth-bridge` (off after Stage B), Netropy OVA VM |

### IP plan (same idea as KVM)

| Role | mgmt | data |
|------|------|------|
| Netropy | `192.168.100.10` | Bridge mode — data IPs not required for L2 path |
| Linux-1 | `192.168.100.21` | `192.168.101.21` on data1 |
| Linux-2 | `192.168.100.22` | `192.168.102.22` on data2 |

Optional **VM Network** NIC on Linux VMs (`192.168.144.x`) for apt/SSH from Windows.

---

## 4. Critical lessons (do not skip)

### NIC order ≠ assumption

ESXi adapter order defines Linux `ens160`, `ens192`, …  
**Always** map IP ↔ port group from **Edit settings**, not from “NIC1 = mgmt” guesswork. Wrong mapping caused ARP / unreachable hosts.

### Manual `ip addr add` is not persistent

Reboot clears lab IPs. Use netplan — see [netplan-examples.md](netplan-examples.md).

### Netropy mgmt on isolated port group

No DHCP → ZeroConf `169.254.x.x` until:

```text
mgmt set addr 192.168.100.10 netmask 255.255.255.0
```

### Web UI from Windows

Tunnel via linux1 VM Network IP:

```bash
ssh -L 8080:192.168.100.10:80 <user>@192.168.144.84
```

Then `http://127.0.0.1:8080`. Keep SSH open.

### ESXi security for Bridging

On `sushanth-data1` and `sushanth-data2` (and/or their vSwitches), set to **Accept**:

- Promiscuous mode  
- MAC address changes  
- Forged transmits  

Without this, Bridging path failed; with it, ping/iperf3 worked.

### UI notes

- **Administration → Emulation Network → Bridge/Route → Forwarding Mode = Bridging**
- Port **Bypass** vs **Drop**: keep **Bypass** (not Drop)
- **License Validation Failed** / Emulation OFF: path test still worked; impairment demo **Needs Product Confirmation**

---

## 5. Stage A / B commands (reference)

**On-link routes (Bridge mode):**

```bash
# linux1 (data NIC that has 192.168.101.21)
sudo ip route replace 192.168.102.0/24 dev ens192

# linux2 (data NIC that has 192.168.102.22)
sudo ip route replace 192.168.101.0/24 dev ens160
```

**iperf3:**

```bash
# linux2
iperf3 -s

# linux1
iperf3 -c 192.168.102.22 -B 192.168.101.21
```

**Verified result (2026-09-21):** ~3.85 Gbit/s through Netropy Bridging.

---

## 6. Acceptance checklist

**Phase 8 (required) — complete**

- [x] Mapping doc  
- [x] ESXi access  
- [x] Three lab networks  
- [x] Stage A Linux bridge path (ping + iperf3)  
- [x] Stage B Netropy OVA + Bridging (ping + iperf3, multi-Gbit/s)  
- [x] Write-up + checklist closed for manual POC  

**Follow-on (not required to close Phase 8)**

- [ ] Impairment/shaping demo (license-limited — mentor may waive)  
- [ ] OpenTofu `modules/esxi/` + CLI parity with KVM  
- [ ] Optional netplan persistence on Linux guests  

---

## 7. Recommended next work (after Phase 8)

1. Confirm with mentor whether impairment demo is required given license failure  
2. Optional: apply netplan on Linux VMs ([netplan-examples.md](netplan-examples.md))  
3. When mentor approves automation: Ubuntu **template** + OVA datastore path + `hashicorp/vsphere` module (Host Client–only ESXi may limit some provider features vs vCenter)  
4. Keep KVM regression green (`example-kvm.json`)  

---

## 8. Verified / Assumed / Unknown / Needs Product Confirmation

### Verified

- Standalone ESXi Host Client lab works for full data path through Netropy Bridging  
- OVA deploy + `engine 1 show` Port 1/2 up  
- `mgmt set addr` static mgmt works  
- ESXi forged transmits / promiscuous Accept required for this Bridging lab  
- iperf3 through Netropy ~3.85 Gbit/s  

### Assumed

- Intern-owned `sushanth-*` networks are acceptable long-term naming  
- Desktop Ubuntu ISO is acceptable (server ISO would be lighter)  

### Unknown

- Whether Host Client–only OpenTofu automation is fully supported without vCenter  

### Needs Product Confirmation

- Valid license / Emulation ON for impairment demo  
- Official ESXi NIC model / sizing for VE 5.1.3 OVA  
- Automation-approved OVA + Linux template workflow  

**Do not commit:** ESXi passwords, OVA binaries, `*.tfstate`, or `lab.auto.tfvars.json`.
