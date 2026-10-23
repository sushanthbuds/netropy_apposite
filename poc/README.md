# Phase 3 Proof of Concept

Boot one Ubuntu VM on local KVM using OpenTofu + libvirt + cloud-init.

This POC validates the tool stack for workbook **Phase 3** (tool selection). The project objective document calls the same work **Phase 0**.

## Prerequisites

- WSL2 Ubuntu with KVM (`kvm-ok` passes)
- OpenTofu installed
- libvirtd running
- Ubuntu cloud image at `../images/noble-server-cloudimg-amd64.img`
- SSH key at `~/.ssh/id_ed25519.pub`

## Commands

```bash
cd ~/netropy-lab/poc
tofu init
tofu plan
tofu apply
tofu output
ssh ubuntu@$(tofu output -raw vm_ip)
tofu destroy
```

If you get permission errors, add your user to the libvirt group:

```bash
sudo usermod -aG libvirt,kvm $USER
newgrp libvirt
```
