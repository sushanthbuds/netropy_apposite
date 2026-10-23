#!/usr/bin/env bash
# Apply the full KVM lab module. Do NOT run with sudo.
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  echo "Do not run this script with sudo. It uses sg libvirt internally." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"
CONFIG="${PROJECT_ROOT}/config/example-kvm.json"
TFVARS="${SCRIPT_DIR}/lab.auto.tfvars.json"
POOL="/var/lib/netropy-lab-pool"

if [[ ! -f "${CONFIG}" ]]; then
  echo "Config not found: ${CONFIG}" >&2
  exit 1
fi

if ! groups | grep -q '\blibvirt\b'; then
  echo "Add your user to the libvirt group, then restart WSL:" >&2
  echo "  sudo usermod -aG libvirt,kvm \$USER" >&2
  exit 1
fi

mkdir -p "${POOL}"

readarray -t LAB_IPS < <(python3 - <<'PY' "${CONFIG}"
import json, sys
from pathlib import Path

config = json.loads(Path(sys.argv[1]).read_text())
instances = config["instances"]
print(instances["linux1"]["mgmt_ip"])
print(instances["linux2"]["mgmt_ip"])
PY
)
LINUX1_MGMT_IP="${LAB_IPS[0]}"
LINUX2_MGMT_IP="${LAB_IPS[1]}"

python3 - <<'PY' "${CONFIG}" "${TFVARS}" "${PROJECT_ROOT}/cli"
import sys
from pathlib import Path

sys.path.insert(0, sys.argv[3])
from netropy_lab.tfvars import write_tfvars
from netropy_lab.validator import validate_config

config = validate_config(Path(sys.argv[1]))
write_tfvars(config, Path(sys.argv[2]))
PY

cd "${SCRIPT_DIR}"
echo "Applying OpenTofu config..."
sg libvirt -c "tofu init -upgrade && tofu apply -auto-approve"

echo ""
echo "Fixing libvirt pool permissions (enter password if prompted)..."
sudo chown -R libvirt-qemu:libvirt "${POOL}" 2>/dev/null || true
sudo chmod 755 "${POOL}"
sudo chmod 660 "${POOL}"/* 2>/dev/null || true
sudo chmod o+x "${HOME}" "${PROJECT_ROOT}"

echo ""
echo "Ensuring VMs autostart and are running..."
for vm in netropy-lab-linux1 netropy-lab-linux2 netropy-lab-netropy; do
  virsh -c qemu:///system autostart "${vm}" >/dev/null 2>&1 || true
  state="$(virsh -c qemu:///system domstate "${vm}" 2>/dev/null || echo missing)"
  if [[ "${state}" == "running" ]]; then
    echo "  ${vm}: already running"
    continue
  fi
  if [[ "${state}" == "missing" ]]; then
    echo "  ${vm}: not found (apply may have failed)" >&2
    continue
  fi
  virsh -c qemu:///system start "${vm}"
  virsh -c qemu:///system qemu-monitor-command "${vm}" --hmp cont >/dev/null 2>&1 || true
  echo "  ${vm}: started"
done

echo ""
echo "Done. Wait ~90 seconds, then run:"
echo "  ping -c 3 ${LINUX1_MGMT_IP}"
echo "  ssh ubuntu@${LINUX1_MGMT_IP}"
echo "  ssh ubuntu@${LINUX2_MGMT_IP}"
