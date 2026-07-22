# Phase 2 — Development Host Setup Verification

**Phase:** 2, Task 2-2  
**Host:** Linux (KVM/libvirt development machine)  
**Date verified:** July 2026  
**Status:** Complete

---

## Purpose

Confirm Python, virtual environment tooling, OpenTofu, KVM/libvirt, and cloud-init-related tooling are available before building the provisioning tool.

**Exit gate (Phase 2):** A fresh shell can run the documented setup checks successfully.

---

## How to run checks

From the repository root:

```bash
chmod +x scripts/verify-setup.sh
./scripts/verify-setup.sh
```

All lines marked **PASS** under required sections must succeed. **WARN** lines are informational.

---

## Verification results

Verified on the development host July 2026.

| Component | Command | Result |
|-----------|---------|--------|
| Python 3 | `python3 --version` | **3.10.12** |
| pip | `python3 -m pip --version` | **22.0.2** |
| venv | `python3 -m venv --help` | **Available** |
| OpenTofu | `tofu version` | **v1.12.4** (linux_amd64) |
| virsh | `virsh --version` | **8.0.0** |
| libvirt connection | `virsh -c qemu:///system list --all` | **OK** — lab VMs listed |
| KVM | `kvm-ok` | **OK** — `/dev/kvm` exists, acceleration usable |
| QEMU | `qemu-system-x86_64 --version` | **6.2.0** |
| libvirt group | `groups` | **OK** — user in `libvirt` group |
| Ubuntu cloud image | `images/noble-server-cloudimg-amd64.img` | **OK** — ~593 MiB |
| Config validation | `netropy-lab validate -c config/example-kvm.json` | **OK** |

### cloud-init note

| Check | Result |
|-------|--------|
| `cloud-init` CLI on host | **Not installed** |
| Guest cloud-init | **Works** — OpenTofu `libvirt_cloudinit_disk` + YAML under `modules/kvm/cloud-init/` |

The host does not require the `cloud-init` package for the current KVM workflow. Cloud-init runs **inside** Ubuntu guests via ISOs created by the libvirt provider. Installing `cloud-init` on the host is optional (useful for debugging guest configs locally).

---

## Sample command output (sanitized)

```
$ python3 --version
Python 3.10.12

$ tofu version
OpenTofu v1.12.4
on linux_amd64

$ virsh --version
8.0.0

$ kvm-ok
INFO: /dev/kvm exists
KVM acceleration can be used

$ virsh -c qemu:///system list --all
 Id   Name                 State
-------------------------------------
  *    netropy-lab-linux1   running
  *    netropy-lab-linux2   running

$ groups
... libvirt ...

$ ls -lh images/noble-server-cloudimg-amd64.img
-rw-r--r-- 1 user user 593M ... noble-server-cloudimg-amd64.img

$ PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json
Config OK: config/example-kvm.json
```

---

## Verified / Assumed / Unknown

### Verified

- Python 3.10+, pip, and venv are installed.
- OpenTofu 1.12.4 is installed and on PATH.
- libvirt/virsh works; user is in the `libvirt` group.
- KVM acceleration is available (`/dev/kvm`, `kvm-ok`).
- Ubuntu 24.04 noble cloud image is present under `images/`.
- Example JSON config passes validation.
- Lab VMs (`netropy-lab-linux1`, `netropy-lab-linux2`) are reachable via libvirt.

### Assumed

- Guest cloud-init via libvirt provider is sufficient without host `cloud-init` CLI.
- Ubuntu image at `/var/lib/netropy-lab-images/` (used by apply script) is the same as repo copy.

### Unknown / optional

- Whether mentor requires host `cloud-init` package installed explicitly.
- WSL2-specific checks if development moves back to WSL (nested virt, `.wslconfig`).

---

## Prerequisites reference (for README)

Install on Ubuntu/Debian if anything fails:

```bash
# Core tooling
sudo apt update
sudo apt install -y python3 python3-pip python3-venv

# OpenTofu — see https://opentofu.org/docs/intro/install/
# KVM / libvirt
sudo apt install -y qemu-kvm libvirt-daemon-system virtinst bridge-utils cpu-checker

# Add user to libvirt group, then log out/in or: newgrp libvirt
sudo usermod -aG libvirt,kvm "$USER"

# Optional: host cloud-init utilities
sudo apt install -y cloud-init cloud-image-utils
```

Download Ubuntu cloud image:

```bash
mkdir -p ~/netropy-lab/images
wget -O ~/netropy-lab/images/noble-server-cloudimg-amd64.img \
  https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
```
