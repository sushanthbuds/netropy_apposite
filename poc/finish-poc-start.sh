#!/usr/bin/env bash
# Finish POC after disk recreate: fix perms, then start VM.
# Run in your terminal:
#   cd ~/netropy-lab/poc && ./finish-poc-start.sh
set -euo pipefail

POOL="$(cd "$(dirname "$0")/.." && pwd)/libvirt-pool"
cd "$(dirname "$0")"

echo "Fixing disk permissions (sudo password may be required)..."
sudo chown -R libvirt-qemu:libvirt "${POOL}"
sudo chmod 755 "${POOL}"
sudo chmod 660 "${POOL}"/*
sudo chmod o+x "${HOME}" "${HOME}/netropy-lab"
ls -la "${POOL}"

echo "Applying / starting domain..."
sg libvirt -c "tofu apply -auto-approve"

virsh -c qemu:///system start netropy-poc-ubuntu >/dev/null 2>&1 || true
sleep 2
virsh -c qemu:///system list --all | grep -E 'Name|netropy-poc' || true

echo ""
echo "Wait ~90–120 seconds for cloud-init, then:"
echo "  ping -c 3 192.168.123.150"
echo "  ssh ubuntu@192.168.123.150"
