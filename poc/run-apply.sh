#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_DIR="$SCRIPT_DIR"
POOL="$(cd "$SCRIPT_DIR/.." && pwd)/libvirt-pool"

if [[ "${EUID}" -eq 0 ]]; then
  echo "ERROR: You ran this with sudo. Do NOT do that."
  echo ""
  echo "Run it as your normal user:"
  echo "  cd ~/netropy-lab/poc"
  echo "  ./run-apply.sh"
  echo ""
  echo "It will ask for your password once on its own for libvirt fixes."
  exit 1
fi

echo "Running as: $(whoami)"
echo "Project dir: $POC_DIR"
echo ""

if ! groups | grep -q '\blibvirt\b'; then
  echo "Adding your user to the libvirt group..."
  sudo usermod -aG libvirt,kvm "$USER"
  echo "Group added. Restart WSL from Windows PowerShell:"
  echo "  wsl --shutdown"
  echo "  wsl"
  exit 1
fi

if ! virsh -c qemu:///system list --all >/dev/null 2>&1; then
  echo "Cannot access libvirt. Restart WSL from Windows PowerShell:"
  echo "  wsl --shutdown"
  echo "  wsl"
  exit 1
fi

cd "$POC_DIR"
mkdir -p "$POOL"

echo "Applying OpenTofu config (no sudo needed for this step)..."
sg libvirt -c "tofu apply -auto-approve"

echo ""
echo "Fixing libvirt pool permissions..."
echo "(Enter your password HERE if prompted - this is normal)"
sudo chown -R libvirt-qemu:libvirt "$POOL" 2>/dev/null || true
sudo chmod 755 "$POOL"
sudo chmod 660 "$POOL"/* 2>/dev/null || true
sudo chmod o+x "$HOME" "$HOME/netropy-lab"

echo ""
echo "Starting VM..."
virsh -c qemu:///system destroy netropy-poc-ubuntu >/dev/null 2>&1 || true
virsh -c qemu:///system start netropy-poc-ubuntu >/dev/null 2>&1 || true
virsh -c qemu:///system qemu-monitor-command netropy-poc-ubuntu --hmp cont >/dev/null 2>&1 || true

echo ""
echo "Done. Wait ~90 seconds, then run:"
echo "  ssh ubuntu@192.168.123.150"
echo "  iperf3 --version"
