#!/usr/bin/env bash
# Phase 2 setup verification — run from a fresh shell in the repo root.
# Exit 0 if all required checks pass; exit 1 otherwise.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

FAIL=0
pass() { echo "  PASS: $*"; }
fail() { echo "  FAIL: $*" >&2; FAIL=1; }
warn() { echo "  WARN: $*"; }

echo "=== Netropy Lab — setup verification ==="
echo "Repo: ${REPO_ROOT}"
echo ""

echo "--- Python ---"
if python3 --version; then pass "python3 available"; else fail "python3 not found"; fi
if python3 -m pip --version >/dev/null 2>&1; then pass "pip available"; else fail "pip not found"; fi
if python3 -m venv --help >/dev/null 2>&1; then pass "venv module available"; else fail "venv module missing"; fi

echo ""
echo "--- OpenTofu ---"
if tofu version; then pass "OpenTofu available"; else fail "tofu not found"; fi

echo ""
echo "--- KVM / libvirt ---"
if virsh --version; then pass "virsh available"; else fail "virsh not found"; fi
if groups | grep -q '\blibvirt\b'; then pass "user in libvirt group"; else fail "user not in libvirt group (run: sudo usermod -aG libvirt,kvm \$USER)"; fi
if [[ -e /dev/kvm ]]; then pass "/dev/kvm exists"; else fail "/dev/kvm missing"; fi
if kvm-ok 2>/dev/null; then pass "KVM acceleration usable"; else warn "kvm-ok failed or not installed — check /dev/kvm manually"; fi
if virsh -c qemu:///system list --all >/dev/null 2>&1; then pass "libvirt qemu:///system reachable"; else fail "cannot connect to qemu:///system"; fi

echo ""
echo "--- QEMU ---"
if qemu-system-x86_64 --version 2>/dev/null | head -1; then pass "qemu-system-x86_64 available"; else fail "qemu-system-x86_64 not found"; fi

echo ""
echo "--- cloud-init (host) ---"
if command -v cloud-init >/dev/null 2>&1; then
  cloud-init --version
  pass "cloud-init CLI on host"
elif dpkg -l cloud-init 2>/dev/null | grep -q "^ii"; then
  pass "cloud-init package installed"
else
  warn "cloud-init not installed on host — OK if using libvirt provider cloud-init disks (see docs/phase_2/setup-verification.md)"
fi

echo ""
echo "--- Ubuntu cloud image ---"
IMAGE_REPO="${REPO_ROOT}/images/noble-server-cloudimg-amd64.img"
IMAGE_SYSTEM="/var/lib/netropy-lab-images/noble-server-cloudimg-amd64.img"
if [[ -f "${IMAGE_REPO}" && -s "${IMAGE_REPO}" ]]; then
  pass "Ubuntu image in repo: ${IMAGE_REPO}"
elif [[ -f "${IMAGE_SYSTEM}" && -s "${IMAGE_SYSTEM}" ]]; then
  pass "Ubuntu image on system: ${IMAGE_SYSTEM}"
else
  fail "Ubuntu noble cloud image not found (expected under images/ or /var/lib/netropy-lab-images/)"
fi

echo ""
echo "--- JSON config validation ---"
if PYTHONPATH="${REPO_ROOT}/cli" python3 -m netropy_lab.cli validate -c "${REPO_ROOT}/config/example-kvm.json"; then
  pass "example-kvm.json validates"
else
  fail "config validation failed"
fi

echo ""
if [[ "${FAIL}" -eq 0 ]]; then
  echo "=== All required checks passed ==="
  exit 0
else
  echo "=== One or more required checks failed ==="
  exit 1
fi
