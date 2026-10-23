#!/bin/bash
# Apply the Phase 3 POC. Do NOT run with sudo.
#
# Disks under ~/netropy-lab/libvirt-pool are created as root:root mode 600.
# QEMU (libvirt-qemu) cannot read them unless we chown BEFORE starting the VM.
# So apply is split: volumes/network first → fix perms → create/start domain.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_DIR="$SCRIPT_DIR"
POOL="$(cd "$SCRIPT_DIR/.." && pwd)/libvirt-pool"

if [[ "${EUID}" -eq 0 ]]; then
  echo "ERROR: Do not run this with sudo."
  echo "  cd ~/netropy-lab/poc && ./run-apply.sh"
  exit 1
fi

echo "Running as: $(whoami)"
echo "Project dir: $POC_DIR"
echo ""

if ! groups | grep -q '\blibvirt\b'; then
  echo "Add your user to libvirt, then log out/in:"
  echo "  sudo usermod -aG libvirt,kvm \$USER"
  exit 1
fi

if ! virsh -c qemu:///system list --all >/dev/null 2>&1; then
  echo "Cannot access libvirt (qemu:///system)."
  exit 1
fi

cd "$POC_DIR"
mkdir -p "$POOL"

fix_pool_perms() {
  echo "Fixing libvirt pool permissions..."
  echo "(Enter your password if prompted)"
  sudo chown -R libvirt-qemu:libvirt "$POOL"
  sudo chmod 755 "$POOL"
  sudo chmod 660 "$POOL"/* 2>/dev/null || true
  sudo chmod o+x "$HOME" "$HOME/netropy-lab"
  ls -la "$POOL"
}

echo "=== Step 1/3: Create pool, network, and disks (no VM start yet) ==="
sg libvirt -c "tofu apply -auto-approve \
  -target=libvirt_pool.lab \
  -target=libvirt_network.lab_net \
  -target=libvirt_cloudinit_disk.ubuntu_ci \
  -target=libvirt_volume.ubuntu_base \
  -target=libvirt_volume.ubuntu_disk \
  -target=libvirt_volume.ubuntu_cloudinit"

echo ""
echo "=== Step 2/3: Fix disk ownership for libvirt-qemu ==="
fix_pool_perms

echo ""
echo "=== Step 3/3: Create and start the VM ==="
sg libvirt -c "tofu apply -auto-approve"

echo ""
echo "Ensuring VM is running..."
virsh -c qemu:///system start netropy-poc-ubuntu >/dev/null 2>&1 || true
virsh -c qemu:///system qemu-monitor-command netropy-poc-ubuntu --hmp cont >/dev/null 2>&1 || true

echo ""
virsh -c qemu:///system list --all | grep -E 'Name|netropy-poc' || virsh -c qemu:///system list --all
echo ""
echo "Done. Wait ~90 seconds for cloud-init, then:"
echo "  cd ~/netropy-lab/poc && tofu output"
echo "  ssh ubuntu@192.168.123.150"
echo "  iperf3 --version"
