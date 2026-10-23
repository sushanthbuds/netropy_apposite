# Phase 8 Step 1 — KVM to vSphere Concept Mapping

**Project:** Netropy VE Automated Provisioning  
**Phase:** 8 — ESXi/vSphere as the second platform  
**Status:** **Phase 8 wrapped up (manual POC, 2026-09-21; docs closeout 2026-09-22)** — see [esxi-setup-checklist.md](esxi-setup-checklist.md) and [phase8-development-guide.md](phase8-development-guide.md). OpenTofu `modules/esxi/` is follow-on.  
**KVM reference:** `modules/kvm/`, `docs/phase_5/phase5-development-guide.md`  
**Example JSON:** `config/example-kvm.json`  
**Active write-up:** [phase8-development-guide.md](phase8-development-guide.md)

---

## Summary in plain language

The **lab recipe stays the same**: Netropy VE plus two Ubuntu Linux VMs on three subnets. Phase 8 on this internship delivered a **working manual ESXi Host Client lab** (Linux bridge POC, then Netropy OVA, Bridging, ping + iperf3 ~3.85 Gbit/s). OpenTofu `modules/esxi/` was deferred until after the manual path succeeded and mentor approves automation.

**Exit gate (manual):** met — ping + iperf3 through Netropy on ESXi without breaking KVM. Impairment demo may need a valid license (**Needs Product Confirmation**).

**Mentor build order (done):** (1) three Linux VMs with middle as bridge, (2) swap for Netropy VE **OVA**. Access via `https://192.168.144.43/ui`, user `root`. Do not commit passwords.

---

## 1. What stays the same across platforms

| Concept | Our lab |
|---------|---------|
| Topology | 1 Netropy VE + 2 Linux traffic endpoints |
| Subnets | mgmt, data-1, data-2 (three isolated L2 segments) |
| JSON contract | `subnets`, `instances`, `options`, `naming_prefix`, `ssh_public_key_file` |
| CLI commands | `validate`, `plan`, `up`, `down`, `verify` (`verify` is KVM-only today) |
| Traffic goal | Linux-1 data → Netropy Port 1 → Netropy Port 2 → Linux-2 data |
| Linux login | `ubuntu@<mgmt_ip>` with SSH public key from JSON |
| Netropy login | `admin@<mgmt_ip>` (password not stored in git) |
| Post-provision config | Operator enables Netropy Bridge mode and adds guest routes (manual today) |

---

## 2. Control plane and tooling

| Aspect | KVM (implemented) | vSphere (Phase 8 target) |
|--------|-------------------|---------------------------|
| Orchestration | OpenTofu >= 1.6 | OpenTofu >= 1.6 |
| Provider | `dmacvicar/libvirt` ~> 0.9 | `hashicorp/vsphere` — **Needs Product Confirmation** on version pin |
| API endpoint | `qemu:///system` (local libvirt) | vCenter or ESXi host FQDN/IP |
| Module path | `modules/kvm/` | `modules/esxi/` (to create) |
| Example config | `config/example-kvm.json` | `config/example-esxi.json` (to create) |
| Who runs apply | Normal user + `sg libvirt` | Workstation or CI with network access to vSphere API |
| Credentials in JSON | None (local socket) | **Never** — use env vars or secret store |

### Suggested ESXi credential env vars (not implemented yet)

| Variable | Purpose |
|----------|---------|
| `VSPHERE_USER` | API user (e.g. `user@domain` or local ESXi user) |
| `VSPHERE_PASSWORD` | Password or token |
| `VSPHERE_SERVER` | vCenter or ESXi hostname |
| `VSPHERE_ALLOW_UNVERIFIED_SSL` | Optional for lab hosts with self-signed certs |

Exact names and auth method are **Needs Product Confirmation** with mentor/IT.

---

## 3. Networking mapping

### KVM today (`modules/kvm/main.tf`)

| Logical subnet | libvirt network name | Host bridge | CIDR (example) | NAT gateway |
|----------------|----------------------|-------------|----------------|-------------|
| Management | `netropy-lab-mgmt` | `virbr-nl-mgmt` | `192.168.100.0/24` | `.1` |
| Data-1 | `netropy-lab-data1` | `virbr-nl-d1` | `192.168.101.0/24` | `.1` |
| Data-2 | `netropy-lab-data2` | `virbr-nl-d2` | `192.168.102.0/24` | `.1` |

- Created by OpenTofu as `libvirt_network` resources with **NAT** forwarding.
- **Static IPs** via libvirt DHCP host entries keyed by **fixed MAC addresses** (more reliable than cloud-init-only on some hosts).
- Linux VMs also get cloud-init network config with the same MAC/IP pairs.

### vSphere target

| KVM concept | vSphere equivalent |
|-------------|-------------------|
| `libvirt_network` | **Port group** on a standard or distributed virtual switch |
| Bridge name (`virbr-nl-*`) | vSwitch / DVS backing the port group |
| NAT + libvirt DHCP | Lab design choice: isolated port groups with a router/NAT VM, corporate VLANs with static IPs, or vSphere/network-team DHCP — **Needs Product Confirmation** |
| Network attachment on VM | NIC connected to named port group |
| `{prefix}-mgmt` naming | Reuse same logical names in docs/CLI; actual port group names come from inventory |

### Port group placeholders (fill with mentor)

| Logical subnet | Planned port group name | VLAN ID | Notes |
|----------------|-------------------------|---------|-------|
| Management | _________________________ | _______ | |
| Data-1 | _________________________ | _______ | |
| Data-2 | _________________________ | _______ | |

### IP plan (unchanged in JSON)

| VM / NIC | IP |
|----------|-----|
| Netropy mgmt | `192.168.100.10` |
| Netropy data-1 / data-2 | `192.168.101.10` / `192.168.102.10` |
| Linux-1 mgmt / data | `192.168.100.21` / `192.168.101.21` |
| Linux-2 mgmt / data | `192.168.100.22` / `192.168.102.22` |

**Open question:** Can the ESXi lab use these same RFC1918 ranges on isolated port groups, or must IPs come from company-assigned subnets?

---

## 4. Storage and images

| Aspect | KVM | vSphere |
|--------|-----|---------|
| Disk pool | libvirt dir pool `/var/lib/netropy-lab-pool` | **Datastore:** _________________________ |
| Linux source image | Ubuntu 24.04 cloud img at `/var/lib/netropy-lab-images/noble-server-cloudimg-amd64.img` | Template or OVA on datastore; content library optional |
| Linux disk format | qcow2 clone in pool | VMDK on datastore |
| Netropy OS disk | `vn-disk1g-5.1.3.qcow2` (~1000 MiB, sda) | From OVA/OVF deploy or converted VMDK |
| Netropy config disk | `vn-disk2-256m-5.1.3.qcow2` (256 MiB, sdb, `/config`) | Second disk from same OVA workflow — **required** |
| JSON field `netropy_image` | Local filesystem path to disk1 | May become template name, content library ID, or datastore path — **Needs Product Confirmation** |
| Disk2 inference | CLI infers sibling `vn-disk2-256m-5.1.3.qcow2` next to disk1 | ESXi module must define equivalent two-disk workflow |

**Lab-proven on KVM:** Missing disk2 caused `<<system error>>` and missing `/config`. ESXi deploy must preserve **two disks in SATA order** (OS first, config second).

---

## 5. VM mapping

### Naming (keep consistent)

| Role | KVM domain name |
|------|-----------------|
| Linux-1 | `netropy-lab-linux1` |
| Linux-2 | `netropy-lab-linux2` |
| Netropy | `netropy-lab-netropy` |

Use `{naming_prefix}-*` on vSphere so CLI summaries and future verify checks stay familiar.

### Linux VMs

| Setting | KVM (`modules/kvm/main.tf`) | vSphere (target) |
|---------|----------------------------|------------------|
| vCPU / RAM | From JSON `options.vcpu` (default 2), `options.memory_mb` (default 2048) | Same from JSON |
| NIC count | 2 (mgmt + data) | 2 |
| NIC 1 network | `{prefix}-mgmt` | Mgmt port group |
| NIC 2 network | `{prefix}-data1` (linux1) or `{prefix}-data2` (linux2) | Matching port group |
| NIC model | `virtio` | **VMXNET3** per project spec — **Needs Product Confirmation** for Netropy; Linux Ubuntu supports VMXNET3 |
| Guest setup | cloud-init ISO (`user_data` + `network_config`) | Guest customization: cloud-init via OVF properties, vApp, or post-deploy script — **Needs Product Confirmation** |
| Packages | iperf3 via cloud-init | Same outcome |
| Autostart | `autostart = true`, CLI ensures running after apply | Power on + optional startup policy |

### Netropy VE 5.1.3

| Setting | KVM (lab-proven) | vSphere (to confirm) |
|---------|------------------|----------------------|
| vCPU | 8 (hardcoded in module) | **Needs Product Confirmation** |
| RAM | 8 GiB (`8388608` KiB) | **Needs Product Confirmation** |
| CPU mode | `host-passthrough` + APIC (required for data ports on KVM) | ESXi CPU compatibility level / feature flags — **Needs Product Confirmation** |
| Disk bus | SATA `sda` + `sdb` | SCSI vs SATA from OVA import — **Needs Product Confirmation** |
| NIC count | 3 | 3 |
| NIC order | mgmt → data-1 → data-2 | Must match product expectation — **Needs Product Confirmation** |
| NIC model | `virtio` (all three on this KVM host) | Project spec suggests **VMXNET3** on ESXi — **Needs Product Confirmation** |
| Provision flag | `options.provision_netropy` | Same JSON flag |

Project objective (`project_objective/Netropy-VE-Provisioning-Intern-Project.md` §11): emulated NICs use **virtio** on KVM and **VMXNET3** on ESXi in Phase 1. Do not assume KVM virtio settings copy verbatim without product validation on vSphere.

---

## 6. OpenTofu resource mapping (design reference)

This table guides `modules/esxi/main.tf` design; resources are **not implemented** yet.

| KVM resource | Purpose | vSphere provider direction |
|--------------|---------|----------------------------|
| `libvirt_pool` | Disk storage directory | Datastore selection via data source |
| `libvirt_network` × 3 | Lab subnets | Use existing port groups (`data "vsphere_network"`) or create if permitted |
| `libvirt_volume` (Linux) | Clone from cloud image | Clone from template / deploy OVA |
| `libvirt_cloudinit_disk` | Linux bootstrap | Guest customization / cloud-init transport |
| `libvirt_domain` (Linux) | 2-NIC Ubuntu VM | `vsphere_virtual_machine` |
| `libvirt_volume` × 2 (Netropy) | OS + config disks | OVF/OVA deploy or attach two VMDKs |
| `libvirt_domain` (Netropy) | 3-NIC emulator | `vsphere_virtual_machine` with 3 NICs |

---

## 7. CLI and tfvars flow

| Step | KVM today | ESXi target |
|------|-----------|-------------|
| 1 | `validate -c config/example-kvm.json` | `validate -c config/example-esxi.json` |
| 2 | `tfvars.py` → `modules/kvm/lab.auto.tfvars.json` | Extend `tfvars.py` or add `esxi_tfvars.py` with vSphere inventory vars |
| 3 | `plan` / `up` / `down` → `kvm.run_tofu(modules/kvm)` | Same CLI dispatch to `modules/esxi/` |
| 4 | Post-apply: `ensure_vms_running` via virsh | Power on VMs via provider or API |
| 5 | Access summary from `outputs.tf` + `cli.py` | Same IP summary from JSON + module outputs |
| 6 | `verify` (Phase 7) | Extend later with vSphere checks (power state, NIC count, port groups) |

`cli/netropy_lab/cli.py` already registers `MODULE_DIRS["esxi"]` but that directory does not exist yet. Implementing `modules/esxi/` so `up` works for `platform: "esxi"` is **follow-on** (not part of Phase 8 manual wrap-up).

### KVM tfvars fields today (`cli/netropy_lab/tfvars.py`)

| Field | Source |
|-------|--------|
| `naming_prefix`, `subnets`, `instances`, `options` | JSON |
| `ssh_public_key` | Read from `ssh_public_key_file` |
| `ubuntu_image` | Fixed host path |
| `netropy_image`, `netropy_config_image` | JSON + disk2 sibling inference |

### Additional ESXi tfvars (planned — names TBD)

| Field | Purpose |
|-------|---------|
| `vsphere_datacenter` | Inventory scope |
| `vsphere_cluster` or `esxi_host` | Compute target |
| `vsphere_datastore` | Disk placement |
| `vsphere_folder` | VM folder (optional) |
| `vsphere_network_mgmt` / `_data1` / `_data2` | Port group names |
| `ubuntu_template` | Linux clone source |
| `netropy_ovf_path` or template name | Netropy deploy workflow |

---

## 8. Verification parity (Phase 7)

| Check layer | KVM implementation | ESXi equivalent |
|-------------|-------------------|-----------------|
| libvirt | `virsh net-list`, `domstate`, `dumpxml` NIC count | vSphere: VM power state, 3 networks attached, NIC count via API |
| management | Host ping + Netropy HTTP | Ping/HTTP from jump host or engineer laptop if routed |
| linux-guest | SSH, cloud-init, `ip -br addr`, iperf3 | Same SSH commands |
| data-path | SSH + ping peer data IP | Same; still requires Netropy Bridge + routes |

`verify` remains KVM-only. ESXi `verify` is **follow-on**. Phase 8 acceptance used **manual** Stage A/B checks (ping + iperf3 through Netropy).

---

## 9. Phase 8 scope boundaries

**Phase 8 delivered (manual wrap-up — complete)**

- KVM→ESXi concept mapping and Host Client checklist
- Working Stage A (Linux bridge) and Stage B (Netropy OVA + Bridging)
- Manual acceptance: ping + iperf3 through Netropy on ESXi
- Document platform-specific limits (security Accept, OVA, static `mgmt set addr`)

**Follow-on (not required to close Phase 8)**

- OpenTofu `modules/esxi/` + `config/example-esxi.json`
- CLI `up` / `down` / `verify` for `platform: "esxi"`
- Optional netplan persistence on Linux guests
- Impairment/shaping demo (license-dependent)

**Out of scope for Phase 8**

- PCI passthrough / SR-IOV on data ports (optional later stretch)
- Changing `modules/kvm/` behavior
- Committing vSphere credentials or tfstate with secrets

---

## 10. Mentor answers (confirmed; no secrets in git)

1. Access type: **Standalone ESXi Host Client** (not vCenter)
2. URL pattern: `https://192.168.144.43/ui` (prefer IP; hostname may fail)
3. Login user: **`root`** (password in password manager only)
4. Datastore: **`esxi-alab2-disk`**
5. Port groups: **`sushanth-mgmt`**, **`sushanth-data1`**, **`sushanth-data2`**
6. Netropy deploy method: **OVA** from shared link (not KVM qcow2)
7. Linux install media: **ISO on datastore** (`iso/ubuntu-24.04.4-desktop-amd64.iso`)
8. Required NIC type/order for Netropy on ESXi: lab used OVA defaults + mapped mgmt/data1/data2 — **Needs Product Confirmation** for official VMXNET3/order guidance
9. VPN required for browser/SSH: **yes** (company VPN)

Day-to-day steps: [esxi-setup-checklist.md](esxi-setup-checklist.md).

---

## 11. Verified / Assumed / Unknown / Needs Product Confirmation

### Verified

- KVM lab topology, names, and IPs documented in `docs/phase_5/phase5-development-guide.md`.
- Mentor: Host Client access; 3 vSwitches + port groups; Linux ISO on datastore; Netropy is OVA; Linux-bridge-first then Netropy.
- **2026-09-21:** Manual Stage A/B complete on ESXi — Bridging + iperf3 ~3.85 Gbit/s through Netropy (`phase8-development-guide.md`).
- ESXi data port-group security Accept required for Bridging path.
- **Phase 8 manual wrap-up closed** — automation deferred.

### Assumed

- Intern `sushanth-*` networks are acceptable for the POC.
- OpenTofu ESXi module waits until mentor requests automation.

### Unknown

- Host Client–only vsphere provider limits without vCenter.

### Needs Product Confirmation

- License / Emulation ON for impairment demo on ESXi.
- Automation-approved OVA + Linux template workflow.
- Official ESXi NIC model / order for VE 5.1.3 OVA.

---

## 12. Next step (after Phase 8)

1. ~~Follow [esxi-setup-checklist.md](esxi-setup-checklist.md) Stage A/B~~ **Done** — see [phase8-development-guide.md](phase8-development-guide.md).
2. Optional: persist guest IPs with [netplan-examples.md](netplan-examples.md).
3. Mentor: waive or require impairment demo; approve OpenTofu `modules/esxi/` if automation is next.

**Do not commit:** vSphere passwords, tokens, `*.tfstate`, or `lab.auto.tfvars.json`.
