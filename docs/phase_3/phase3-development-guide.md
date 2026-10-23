# Phase 3 — Development Instructions Guide

**Project:** Netropy VE Automated Provisioning  
**Phase:** 3 — Provisioning Tool Selection and Proof-of-Concept  
**Related write-up:** `docs/phase_3/phase3-tool-recommendation.md`  
**POC code:** `poc/`  

> Note: The project objective document calls this same work **Phase 0**. The workbook and this repo use **Phase 3**.

---

## 1. Purpose of Phase 3

Phase 3 answers two questions before building the full 3-VM lab:

1. **Which tools should we use** to provision labs on KVM (and later ESXi/AWS)?
2. **Do those tools actually work together** on this development host?

We prove the stack with a **small proof-of-concept (POC)**: one Ubuntu VM on KVM using OpenTofu + libvirt + cloud-init. If apply, SSH, iperf3, and destroy all work, the tool choice is validated.

Phase 3 does **not** build the full Netropy lab (that is later). It only de-risks the toolchain.

---

## 2. Recommended stack (what we chose and why)

| Layer | Choice | Why |
|-------|--------|-----|
| IaC engine | **OpenTofu** | Declarative create/destroy with state; Terraform-compatible; open MPL-2.0 license |
| KVM API | **dmacvicar/libvirt** provider | Creates pools, networks, disks, cloud-init ISOs, and VMs on `qemu:///system` |
| Guest bootstrap | **cloud-init** | Standard first-boot setup on Ubuntu cloud images (user, SSH key, packages, IP) |
| User UX (later) | **Thin Python CLI** | Validate JSON → run OpenTofu → print access summary |

We rejected using only `virsh`/`virt-install` as the long-term tool because that would mean three separate imperative codebases for KVM, ESXi, and AWS.

---

## 3. Files involved in Phase 3

| Path | Role |
|------|------|
| `poc/main.tf` | Declares pool, NAT network, disks, cloud-init disk, and the VM |
| `poc/outputs.tf` | Exposes VM name, IP, SSH command, next steps |
| `poc/cloud-init/user-data.yaml` | First-boot user, SSH key, packages (`iperf3`, `qemu-guest-agent`) |
| `poc/run-apply.sh` | Safe apply: create disks → fix permissions → start VM |
| `poc/run-destroy.sh` | Destroy OpenTofu resources and clean leftover libvirt objects |
| `poc/README.md` | Short POC usage notes |
| `images/noble-server-cloudimg-amd64.img` | Ubuntu 24.04 cloud base image (local; not always in git) |
| `libvirt-pool/` | Runtime disk storage for the POC (gitignored) |
| `docs/phase_3/phase3-tool-recommendation.md` | Formal recommendation + results write-up |

---

## 4. Prerequisites (check before starting)

Run these from a normal user shell (not root).

### 4.1 Confirm KVM is usable

```bash
kvm-ok
```

**Why:** Confirms the CPU and kernel support hardware virtualization.  
**How:** If it prints that KVM acceleration can be used, proceed. If not, fix BIOS/nested virt / WSL settings first.

### 4.2 Confirm libvirt access

```bash
groups
virsh -c qemu:///system list --all
```

**Why:** OpenTofu talks to libvirt as your user via the `libvirt` group.  
**How:** `groups` should include `libvirt` (and usually `kvm`). The `virsh` command should list domains (even if empty), not permission errors.

If needed:

```bash
sudo usermod -aG libvirt,kvm $USER
# then log out/in, or:
newgrp libvirt
```

**Why `usermod`:** Adds your account to the groups that can manage system libvirt.  
**Why `newgrp`:** Activates the new group in the current session without a full logout.

### 4.3 Confirm OpenTofu

```bash
tofu version
```

**Why:** Phase 3 uses OpenTofu (`tofu`), not the HashiCorp `terraform` binary (unless company policy says otherwise).  
**How:** Expect OpenTofu >= 1.6 (POC was validated with v1.12.x).

### 4.4 Confirm Ubuntu cloud image and SSH key

```bash
ls -lh ~/netropy-lab/images/noble-server-cloudimg-amd64.img
ls ~/.ssh/id_ed25519.pub
```

**Why:** `main.tf` chains the VM disk from that image and injects your public key via cloud-init.  
**How:** Both paths must exist. Generate a key with `ssh-keygen -t ed25519` if missing (do not commit private keys).

### 4.5 Optional host-wide setup check

```bash
cd ~/netropy-lab
./scripts/verify-setup.sh
```

**Why:** Phase 2 script that checks Python, OpenTofu, libvirt, image, and related tools in one place.

---

## 5. Initialize the POC (first time in `poc/`)

```bash
cd ~/netropy-lab/poc
tofu init
```

**What it does:** Downloads the `dmacvicar/libvirt` provider into `.terraform/` and prepares the working directory.  
**Why:** Required once (or after provider/version changes) before `plan`/`apply`.  
**How it was used:** Run from `poc/` so OpenTofu finds `main.tf` and `.terraform.lock.hcl`.

Inspect the plan without changing anything:

```bash
tofu plan
```

**What it does:** Shows what would be created (pool, network, volumes, cloud-init disk, domain).  
**Why:** Safe review before apply; catches missing image path or syntax issues early.

---

## 6. Apply the POC (recommended: `./run-apply.sh`)

Prefer the wrapper script over a bare `tofu apply`, because of libvirt disk permissions.

```bash
cd ~/netropy-lab/poc
chmod +x run-apply.sh run-destroy.sh
./run-apply.sh
```

### 6.1 Why not `sudo ./run-apply.sh`?

The script **refuses root**. With `sudo`, `$HOME` and SSH key paths break, and disks/ownership become harder to fix. Always run as your normal user.

### 6.2 What `run-apply.sh` does (step by step)

#### Step A — Safety checks

- Confirms you are not root  
- Confirms you are in the `libvirt` group  
- Confirms `virsh -c qemu:///system` works  
- Creates `../libvirt-pool` if needed  

#### Step B — Create storage/network/disks first (no full VM start yet)

```bash
sg libvirt -c "tofu apply -auto-approve \
  -target=libvirt_pool.lab \
  -target=libvirt_network.lab_net \
  -target=libvirt_cloudinit_disk.ubuntu_ci \
  -target=libvirt_volume.ubuntu_base \
  -target=libvirt_volume.ubuntu_disk \
  -target=libvirt_volume.ubuntu_cloudinit"
```

| Part | Meaning |
|------|---------|
| `sg libvirt -c "..."` | Run the command with the `libvirt` group active (needed for socket access) |
| `tofu apply -auto-approve` | Create/update resources without interactive yes/no |
| `-target=...` | Apply only listed resources first |

**Why targeted apply:** Disks under `libvirt-pool/` can be created with ownership QEMU cannot read. Fix permissions **before** starting the domain, or the VM fails to boot.

#### Step C — Fix pool permissions

```bash
sudo chown -R libvirt-qemu:libvirt "$POOL"
sudo chmod 755 "$POOL"
sudo chmod 660 "$POOL"/* 2>/dev/null || true
sudo chmod o+x "$HOME" "$HOME/netropy-lab"
```

**Why:** QEMU runs as `libvirt-qemu` and must read the qcow2 disks. Also needs execute permission on parent directories to traverse into the pool.  
**How:** `sudo` is used only for these permission fixes, not for the whole apply.

#### Step D — Create and start the VM

```bash
sg libvirt -c "tofu apply -auto-approve"
```

**Why:** Second apply creates/starts `libvirt_domain` now that disks are readable.

#### Step E — Ensure the guest is running

```bash
virsh -c qemu:///system start netropy-poc-ubuntu
virsh -c qemu:///system qemu-monitor-command netropy-poc-ubuntu --hmp cont
virsh -c qemu:///system list --all
```

**Why:** Sometimes the domain exists but is shut off/paused; these commands start it and confirm state.

### 6.3 Alternative: manual OpenTofu (simpler hosts)

If permissions are already correct:

```bash
cd ~/netropy-lab/poc
tofu init
tofu apply
```

**Why this may be enough:** Same end state, but without the script’s permission staging. Prefer `./run-apply.sh` on this project host.

---

## 7. What the POC creates (from `main.tf`)

| Resource | Name / value | Purpose |
|----------|--------------|---------|
| Storage pool | `netropy-poc` → `libvirt-pool/` | Where VM disks live |
| Network | `netropy-poc-net` (NAT `192.168.123.0/24`) | Isolated lab network with DHCP range |
| Base volume | Ubuntu noble cloud image copy | Backing image |
| Overlay disk | `netropy-poc-ubuntu.qcow2` (10 GiB) | Writable VM disk |
| Cloud-init disk | NoCloud ISO | First-boot config |
| Domain (VM) | `netropy-poc-ubuntu` | 2 vCPU, 2 GB RAM (as configured) |
| Static IP | `192.168.123.150` | Assigned via cloud-init / MAC match |

Cloud-init (`poc/cloud-init/user-data.yaml`) creates user `ubuntu`, installs your SSH public key, and installs `iperf3` + `qemu-guest-agent`.

---

## 8. Verify the POC after apply

Wait about **90 seconds** for cloud-init to finish package install and networking.

### 8.1 Read OpenTofu outputs

```bash
cd ~/netropy-lab/poc
tofu output
tofu output -raw vm_ip
```

**Why:** Workbook requires exposing the management IP as an output.  
**How:** `tofu output` shows all outputs; `-raw vm_ip` prints only the IP for scripts/SSH.

### 8.2 SSH into the VM

```bash
ssh ubuntu@$(tofu output -raw vm_ip)
# or directly:
ssh ubuntu@192.168.123.150
```

**Why:** Proves management reachability and that cloud-init injected your SSH key.  
**How:** Uses the `ubuntu` user from cloud-init and the key from `~/.ssh/id_ed25519.pub`.

### 8.3 Confirm iperf3

```bash
iperf3 --version
```

**Why:** The future lab uses iperf3 as the traffic generator; the POC proves package install via cloud-init works.

### 8.4 Optional libvirt inspection

```bash
virsh -c qemu:///system dominfo netropy-poc-ubuntu
virsh -c qemu:///system domifaddr netropy-poc-ubuntu
```

**Why:** Confirms the domain exists, is running, and shows interface/address info from libvirt’s view.

---

## 9. Destroy the POC

```bash
cd ~/netropy-lab/poc
./run-destroy.sh
```

### What destroy does

1. **`sg libvirt -c "tofu destroy -auto-approve"`**  
   Removes resources tracked in OpenTofu state (VM, volumes, network, pool, etc.).

2. **Leftover cleanup with virsh** (in case state and libvirt drifted):

```bash
virsh -c qemu:///system destroy netropy-poc-ubuntu    # force power-off
virsh -c qemu:///system undefine netropy-poc-ubuntu   # remove VM definition
virsh -c qemu:///system net-destroy netropy-poc-net
virsh -c qemu:///system net-undefine netropy-poc-net
virsh -c qemu:///system pool-destroy netropy-poc
virsh -c qemu:///system pool-undefine netropy-poc
```

| Command | Meaning |
|---------|---------|
| `destroy` (virsh) | Immediate power-off (like pulling the plug) |
| `undefine` | Remove the libvirt object definition |
| `net-destroy` / `pool-destroy` | Stop network / pool |
| `net-undefine` / `pool-undefine` | Remove their definitions |

3. **Remove leftover disk files** in `libvirt-pool/` with `sudo rm` if needed.

**Why a wrapper:** OpenTofu destroy alone can leave orphans if a prior apply failed mid-way; the script makes teardown repeatable.

Manual alternative:

```bash
cd ~/netropy-lab/poc
tofu destroy
```

---

## 10. Helper scripts (recovery)

If apply fails partway, helpers under `poc/` may exist:

| Script | Typical use |
|--------|-------------|
| `fix-and-reapply.sh` | Repair permissions / re-run apply after a failed attempt |
| `finish-poc-start.sh` | Finish starting the VM if disks exist but domain did not start |

Always prefer understanding `run-apply.sh` first; use helpers only when recovering from a broken mid-state.

---

## 11. Key lessons learned in Phase 3

1. **libvirt provider v0.9** uses object-style HCL (not older block syntax).  
2. **Do not run apply with sudo** — breaks `$HOME` and SSH key paths.  
3. **Pool permissions matter** — QEMU must own/read disks under `libvirt-pool/`.  
4. **cloud-init static IP via MAC match works** — pattern scales to multi-NIC VMs later.  
5. **OpenTofu + libvirt is viable** on the intern host for KVM-first development.

---

## 12. Phase 3 exit criteria (self-check)

You can mark Phase 3 complete when:

- [ ] Tool recommendation is written (`phase3-tool-recommendation.md`)
- [ ] `tofu init` / apply (or `./run-apply.sh`) succeeds
- [ ] You can SSH to the POC VM
- [ ] `iperf3 --version` works inside the guest
- [ ] `./run-destroy.sh` (or `tofu destroy`) cleans up
- [ ] You can explain this phase in your own words (see below)

---

## 13. Explain Phase 3 in your own words (student self-check)

Phase 3 was tool selection plus a small proof. I compared provisioning options and chose OpenTofu with the libvirt provider and cloud-init. I proved that stack by creating one Ubuntu VM on KVM that boots, gets an IP, installs iperf3, and destroys cleanly. That unblocks building the full lab later; Phase 3 itself is not the full Netropy topology.

---

## 14. What comes next

- **Phase 4** — JSON configuration contract: schema, stronger `validate`, unit tests (no provisioning).  
- **Phase 5** — Full KVM lab: 3 networks, 2 Linux VMs, Netropy VE (`docs/phase_5/phase5-development-guide.md`).

---

## 15. Quick command cheat sheet

```bash
# Setup checks
kvm-ok
virsh -c qemu:///system list --all
tofu version

# POC lifecycle
cd ~/netropy-lab/poc
tofu init
./run-apply.sh
# wait ~90s
tofu output
ssh ubuntu@192.168.123.150
iperf3 --version
./run-destroy.sh
```

---

**Document status:** Development instructions for Phase 3 (intern reference).  
**Do not commit:** secrets, private keys, `*.tfstate`, or contents of `libvirt-pool/`.
