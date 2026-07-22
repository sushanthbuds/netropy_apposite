#!/usr/bin/env bash
# Destroy the full KVM lab module. Do NOT run with sudo.
set -euo pipefail

if [[ "${EUID:-$(id -u)}" -eq 0 ]]; then
  echo "Do not run this script with sudo. It uses sg libvirt internally." >&2
  exit 1
fi

confirm_destroy() {
  if [[ "${NETROPY_LAB_CONFIRM_DESTROY:-}" == "yes" || "${1:-}" == "--yes" ]]; then
    return 0
  fi
  echo "WARNING: This destroys the full KVM lab (VMs, networks, and related state)." >&2
  echo "See docs/phase_2/security-guardrails.md" >&2
  read -r -p "Type 'destroy' to confirm: " answer
  if [[ "${answer}" != "destroy" ]]; then
    echo "Aborted." >&2
    exit 1
  fi
}

confirm_destroy "${1:-}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "${SCRIPT_DIR}"
sg libvirt -c "tofu destroy -auto-approve"
