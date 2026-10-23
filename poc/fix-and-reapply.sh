#!/usr/bin/env bash
# Reset and re-apply the Phase 3 POC with correct permission ordering.
# Run in YOUR terminal (needs sudo password):
#   cd ~/netropy-lab/poc && ./fix-and-reapply.sh
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  echo "Do not run this whole script with sudo. Run as your user:" >&2
  echo "  ./fix-and-reapply.sh" >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
POOL="$(cd "${SCRIPT_DIR}/.." && pwd)/libvirt-pool"

cd "${SCRIPT_DIR}"

echo "=== Destroying existing POC (if any) ==="
sg libvirt -c "tofu destroy -auto-approve" || true
virsh -c qemu:///system destroy netropy-poc-ubuntu >/dev/null 2>&1 || true
virsh -c qemu:///system undefine netropy-poc-ubuntu >/dev/null 2>&1 || true

# If destroy left root-owned files, clear them so the next apply is clean
if [[ -d "${POOL}" ]]; then
  echo "Cleaning pool directory (sudo may ask for password)..."
  sudo rm -rf "${POOL}"
fi
mkdir -p "${POOL}"
sudo chown libvirt-qemu:libvirt "${POOL}"
sudo chmod 755 "${POOL}"
sudo chmod o+x "${HOME}" "${HOME}/netropy-lab"

echo ""
echo "=== Re-applying with two-phase permission fix ==="
./run-apply.sh

echo ""
echo "Verify:"
echo "  virsh -c qemu:///system list --all | grep netropy-poc"
echo "  tofu output"
echo "  # wait ~90s then: ssh ubuntu@192.168.123.150"
