#!/usr/bin/env bash
# Fix libvirt pool permissions so QEMU can read VM disks. Run after apply if VMs fail to boot.
set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POOL="/var/lib/netropy-lab-pool"

echo "Fixing permissions on ${POOL}..."
sudo chown -R libvirt-qemu:libvirt "${POOL}"
sudo chmod 755 "${POOL}"
sudo chmod 660 "${POOL}"/* 2>/dev/null || true
sudo chmod o+x "${HOME}" "${HOME}/netropy-lab"
echo "Done."

for vm in netropy-lab-linux1 netropy-lab-linux2; do
  if virsh -c qemu:///system dominfo "${vm}" >/dev/null 2>&1; then
    echo "Restarting ${vm}..."
    virsh -c qemu:///system destroy "${vm}" >/dev/null 2>&1 || true
    virsh -c qemu:///system start "${vm}"
    virsh -c qemu:///system qemu-monitor-command "${vm}" --hmp cont >/dev/null 2>&1 || true
  fi
done
