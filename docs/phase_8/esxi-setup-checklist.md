# ESXi Netropy Lab — Setup Checklist

**Project:** Netropy VE Automated Provisioning  
**Phase:** 8 — Manual ESXi POC  
**Status:** **Phase 8 wrapped up (manual POC)** — 2026-09-21; docs closeout 2026-09-22  
**Write-up:** [phase8-development-guide.md](phase8-development-guide.md)  
**Related:** [kvm-to-vsphere-mapping.md](kvm-to-vsphere-mapping.md)

Ground truth from mentor call + intern lab. Do **not** invent beyond this document.  
**Do not commit:** ESXi passwords, tokens, or secrets.

---

## 0. Access

- [x] Connect to company VPN
- [x] Open ESXi Host Client in a browser
- [x] Prefer **IP** if hostname does not resolve (hostname failed in mentor session)
- [x] URL pattern: `https://192.168.144.43/ui`
- [x] Record verified IP locally (do not put passwords in git)
- [x] Login user: **`root`**
- [x] Password: store in password manager only
- [x] Accept certificate warning if shown (lab host)
- [x] Note existing VMs — **do not modify other people’s VMs**

---

## 1. Networking (ESXi UI → Networking)

- [x] Create vSwitch for **management** → `vSwitch-sushanth-mgmt` (0 uplinks)
- [x] Create port group → `sushanth-mgmt`
- [x] Create vSwitch for **data network 1** → `vSwitch-sushanth-data1`
- [x] Create port group → `sushanth-data1`
- [x] Create vSwitch for **data network 2** → `vSwitch-sushanth-data2`
- [x] Create port group → `sushanth-data2`

| Role | vSwitch name | Port group name |
|------|--------------|-----------------|
| Management | `vSwitch-sushanth-mgmt` | `sushanth-mgmt` |
| Data-1 | `vSwitch-sushanth-data1` | `sushanth-data1` |
| Data-2 | `vSwitch-sushanth-data2` | `sushanth-data2` |

**Required for Netropy Bridging:** port group (or vSwitch) Security → Promiscuous / MAC changes / Forged transmits = **Accept**.

---

## 2. Storage / images

- [x] Datastore browser on `esxi-alab2-disk`
- [x] Linux ISO: `iso/ubuntu-24.04.4-desktop-amd64.iso`
- [x] Netropy VE **OVA** from mentor shared link (`vn-disk1g-5.1.3`)
- [x] Datastore: `esxi-alab2-disk`

---

## 3. Stage A — Linux bridge POC

- [x] Linux-1 — `sushanth-linux1` (mgmt + data1)
- [x] Linux-2 — `sushanth-linux2` (mgmt + data2)
- [x] Linux-Bridge — `sushanth-bridge` (mgmt + data1 + data2)
- [x] Install `iperf3` via apt (temporary `VM Network` NIC for internet)
- [x] Ping through Linux bridge
- [x] iperf3 through Linux bridge (multi-Gbit/s)

---

## 4. Stage B — Netropy VE

- [x] Deploy Netropy from **OVA** (map VM Network→mgmt, TestNetwork-1→data1, TestNetwork-2→data2)
- [x] Power off Linux bridge after cutover
- [x] `mgmt set addr 192.168.100.10 netmask 255.255.255.0`
- [x] UI via SSH tunnel; Bridge/Route → **Bridging**
- [x] Ping linux1 ↔ linux2 through Netropy
- [x] iperf3 through Netropy (~3.85 Gbit/s verified 2026-09-21)
- [ ] Shaping/impairment demo — **follow-on / Needs Product Confirmation** (License Validation Failed / Emulation often OFF; not required to close Phase 8)

---

## 5. Timeline

- [x] No hard demo deadline — deliver when ready
- [x] Phase 8 manual POC wrapped up (docs aligned 2026-09-22)

---

## 6. Mentor follow-ups (post–Phase 8)

1. Is impairment demo required given license failure?
2. Approve OpenTofu `modules/esxi/` as next work?
3. Password rotation for shared `root` if needed

---

## 7. What comes after Phase 8

| When | Do |
|------|-----|
| Optional | netplan persistence ([netplan-examples.md](netplan-examples.md)); screenshots for mentor |
| Next (if mentor approves) | OpenTofu `modules/esxi/` (template/OVA automation design) |
| Avoid | Committing secrets |

---

## 8. Verified / Assumed / Unknown / Needs Product Confirmation

### Verified

- Full Stage A and Stage B path on this ESXi host
- OVA + Bridging + ESXi security Accept + static mgmt IP
- iperf3 through Netropy ~3.85 Gbit/s
- See [phase8-development-guide.md](phase8-development-guide.md)

### Assumed

- `sushanth-*` naming is fine for intern lab cleanup later

### Unknown

- Host-only OpenTofu vsphere provider limits without vCenter

### Needs Product Confirmation

- License / Emulation ON for impairment between sessions

**Do not commit:** passwords, `*.tfstate`, or OVA binaries into git.
