#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POC_DIR="$SCRIPT_DIR"
POOL="$(cd "$SCRIPT_DIR/.." && pwd)/libvirt-pool"

if [[ "${EUID}" -eq 0 ]]; then
  echo "Do not run this script with sudo. Run: ./run-destroy.sh"
  exit 1
fi

cd "$POC_DIR"

echo "Destroying OpenTofu-managed resources..."
sg libvirt -c "tofu destroy -auto-approve" || true

echo "Cleaning up any leftover libvirt resources..."
virsh -c qemu:///system destroy netropy-poc-ubuntu >/dev/null 2>&1 || true
virsh -c qemu:///system undefine netropy-poc-ubuntu >/dev/null 2>&1 || true
virsh -c qemu:///system net-destroy netropy-poc-net >/dev/null 2>&1 || true
virsh -c qemu:///system net-undefine netropy-poc-net >/dev/null 2>&1 || true
virsh -c qemu:///system pool-destroy netropy-poc >/dev/null 2>&1 || true
virsh -c qemu:///system pool-undefine netropy-poc >/dev/null 2>&1 || true

echo "Removing leftover disk files..."
sudo rm -f "$POOL"/* 2>/dev/null || true

echo "Reset complete. Run ./run-apply.sh to start fresh."
