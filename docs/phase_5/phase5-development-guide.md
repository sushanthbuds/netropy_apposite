# Phase 5 — Development Instructions Guide

**Project:** Netropy VE Automated Provisioning  
**Phase:** 5 — Full KVM lab (3 networks, 2 Linux VMs, Netropy VE)  
**Module:** `modules/kvm/`  
**Example JSON:** `config/example-kvm.json`  

> Phase 5 is the intern-workbook name for the full KVM topology. The project spec calls the same outcome **Phase 1a — KVM end-to-end**.

---

## 1. Purpose of Phase 5

Stand up the **three-VM lab on one KVM host** from JSON + OpenTofu, then prove traffic can flow:

**Linux-1 data → Netropy Port 1 → Netropy Port 2 → Linux-2 data**

Phase 5 does **not** finish the Python `up`/`down`/`verify` CLI (Phase 6–7) or ESXi.

---

## 2. What this host actually runs

| VM | Domain | Role |
|----|--------|------|
| Netropy VE 5.1.3 | `netropy-lab-netropy` | Emulator (mgmt + 2 data ports) |
| Linux-1 | `netropy-lab-linux1` | iperf3 client endpoint |
| Linux-2 | `netropy-lab-linux2` | iperf3 server endpoint |

| Subnet | CIDR | Bridge | Members |
|--------|------|--------|---------|
| Management | `192.168.100.0/24` | `virbr-nl-mgmt` | all three mgmt NICs |
| Data-1 | `192.168.101.0/24` | `virbr-nl-d1` | Netropy Port 1, Linux-1 data |
| Data-2 | `192.168.102.0/24` | `virbr-nl-d2` | Netropy Port 2, Linux-2 data |

**IPs**

| NIC | IP |
|-----|-----|
| Netropy mgmt | `192.168.100.10` |
| Netropy data-1 / data-2 | `192.168.101.10` / `192.168.102.10` (JSON; **no ping in Bridge mode**) |
| Linux-1 mgmt / data | `192.168.100.21` / `192.168.101.21` |
| Linux-2 mgmt / data | `192.168.100.22` / `192.168.102.22` |

---

## 3. Files involved in Phase 5

| Path | Role |
|------|------|
| `modules/kvm/main.tf` | Networks, Linux VMs, Netropy domain (disks, NICs, CPU) |
| `modules/kvm/variables.tf` | JSON-backed variables |
| `modules/kvm/outputs.tf` | Access summary / iperf3 reminder |
| `modules/kvm/run-apply.sh` | Generate tfvars, `tofu apply`, pool permissions |
| `modules/kvm/run-destroy.sh` | Tear down the lab |
| `modules/kvm/cloud-init/` | Ubuntu user, SSH key, static IPs, iperf3 |
| `config/example-kvm.json` | Lab IPs, image path, `provision_netropy: true` |
| `Netropy-VM/vn-disk1g-5.1.3.qcow2` | OVA disk1 (OS) — local, not in git |
| `Netropy-VM/vn-disk2-256m-5.1.3.qcow2` | OVA disk2 (`/config`) — local, not in git |

---

## 4. Netropy VE on KVM (lab-proven)

Do not guess these from generic KVM docs. This is what worked for **VE 5.1.3** on this host.

| Setting | What to use |
|---------|-------------|
| Disks | **Two** SATA disks: OS `sda`, config `sdb`. One disk → `<<system error>>` and `/config` missing |
| NICs | **virtio** on all three, order **mgmt → data-1 → data-2** |
| CPU | `host-passthrough` (Xeon flags). Default qemu64 (`QEMU Virtual CPU version 2.5+`) → `<<no data ports>>` |
| RAM | 8 GiB (`memory = 8388608` KiB in `main.tf`) |
| vCPU | Netropy domain is **hardcoded to 8**; JSON `options.vcpu` applies to **Linux VMs only** |
| Forwarding | Administration → **Bridge/Route** → Bridging |

A known-working domain XML from another KVM host used virtio on all NICs, 2 vCPU, 8 GiB, and SATA. This lab used host-passthrough instead of pinning IvyBridge so the guest saw the PowerEdge Xeon ISA.

**CLI check that data ports exist**

```text
engine 1 show
```

Expected: `Port 1: up`, `Port 2: up`, `Path 1` present. Engine number is **1** (`engine 0 show` is invalid).

---

## 5. Management access (web UI)

Netropy HTTP is on **port 80** at the mgmt IP. HTTPS was not usable on this lab.

**On the KVM host**

```text
http://192.168.100.10:80
```

**From Windows Chrome** — `192.168.100.10` is only on the lab NAT. SSH does not expose it. Use a tunnel and leave it open:

```bash
ssh -L 8080:192.168.100.10:80 soumi@<kvm-host>
```

Then open:

```text
http://127.0.0.1:8080
```

SSH user is `admin`. Do not put the password in git or JSON.

---

## 6. Provision (do not use sudo for tofu)

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json

cd ~/netropy-lab/modules/kvm
./run-apply.sh
```

Wait ~90 seconds for Linux cloud-init. Confirm:

```bash
virsh -c qemu:///system list --all
ping -c 3 192.168.100.10
ping -c 3 192.168.100.21
ping -c 3 192.168.100.22
ssh ubuntu@192.168.100.21
ssh ubuntu@192.168.100.22
```

Destroy (explain impact first: all three lab VMs and networks go away):

```bash
cd ~/netropy-lab/modules/kvm
./run-destroy.sh
```

---

## 7. iperf3 through Netropy (Phase 5 exit test)

Linux data NICs are on **two different /24s**. Bridge mode forwards L2 between Port 1 and Port 2 but does not install those routes. Add on-link routes (until reboot), then test:

```bash
# Linux-1
sudo ip route replace 192.168.102.0/24 dev ens4

# Linux-2
sudo ip route replace 192.168.101.0/24 dev ens4

# Linux-2
iperf3 -s

# Linux-1
iperf3 -c 192.168.102.22 -B 192.168.101.21
```

**Result on this host (2026-08-27):** ping both ways OK; iperf3 ~7 Gbit/s for 5 seconds. Netropy `192.168.101.10` / `192.168.102.10` do **not** answer ping in Bridge mode (expected).

High bitrate means **emulation impairments are off**. Traffic still crosses the two data ports.

---

## 8. License vs intern path test

The UI shows **License Validation Failed**. `engine 1 emulation on` returns `Invalid or expired license`.

Mentor guidance on this lab: **license does not block the intern path test**. Bridging still forwarded frames with Emulation off.

A licensed **Emulation on** run (rate-limit / delay) was **not** executed. If sign-off requires visible WAN impairments, that still needs a valid key (**Upgrade → License Key**).

---

## 9. Phase 5 exit criteria (self-check)

- [ ] Three libvirt networks and three VMs come from `./run-apply.sh`
- [ ] Linux-1 / Linux-2 have JSON IPs; iperf3 installed
- [ ] Netropy boots; SSH/UI on `192.168.100.10:80`
- [ ] `engine 1 show` lists Port 1 and Port 2 up
- [ ] Bridging selected; iperf3 Linux-1 → Linux-2 on the data NICs
- [ ] Teardown via `./run-destroy.sh` is documented
- [ ] Product details above are written down (this file)
- [ ] You can explain the packet path without the spec

---

## 10. Explain Phase 5 in your own words (student self-check)

Phase 5 built the real KVM lab: management plus two data networks, two Ubuntu iperf3 VMs, and Netropy VE 5.1.3. Netropy needed both OVA disks on SATA, virtio NICs, and host CPU passthrough so it would detect data ports. The web UI is HTTP on the management IP (tunnel from Windows). With Bridging and emulation off, iperf3 still ran through Port 1 and Port 2. Turning emulation on needs a license; that was out of scope after mentor said the license does not matter for this check.

---

## 11. What comes next

- **Phase 6** — Done. CLI `validate` / `plan` / `up` / `down` — `docs/phase_6/phase6-development-guide.md`
- **Phase 7** — `verify` command (pings + optional iperf3)
- Optional: bake the on-link data routes into cloud-init so the iperf3 command works after reboot without extra `ip route` lines

---

## 12. Verified / Assumed / Unknown / Needs Product Confirmation

### Verified

- Three VMs, three networks, Linux IPs and iperf3 3.16.
- Netropy mgmt ping/HTTP; UI login; `engine 1 show` Port 1/2 up.
- virtio × 3, SATA `sda`/`sdb`, `cpu mode=host-passthrough`.
- iperf3 through the data path with Bridging and emulation off.

### Assumed

- Mentor accepts emulation-off iperf3 as the Phase 5 traffic proof.
- JSON `vcpu` / `memory_mb` remaining Linux-only is acceptable for now.

### Unknown

- Whether cloud-init should add the extra data-subnet routes by default.

### Needs Product Confirmation

- Official VE 5.1.3 license requirements for **Emulation on**.
- Whether 2 vCPU (working `vnwe` XML) vs 8 vCPU (this module) is required.
- Config disk `qcow2` vs `raw` (working XML used `raw` for disk2; this lab uses qcow2).

---

**Document status:** Development instructions for Phase 5 (intern reference).  
**Do not commit:** secrets, private keys, `*.tfstate`, `lab.auto.tfvars.json`, or Netropy qcow2 images.
