#!/usr/bin/env bash
# Build a clean, shareable tarball of the KVM demo lab: dist/netropy-kvm-demo.tar.gz
# Copies an explicit allowlist only — no tfstate, generated tfvars, images, keys, or .git.
# Exit 0 on success; exit 1 if the staged package fails the safety checks.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="netropy-kvm-demo"
DIST_DIR="${REPO_ROOT}/dist"
OUT="${DIST_DIR}/${NAME}.tar.gz"
PACKAGE_NETROPY_IMAGE="/var/lib/netropy-lab-images/vn-disk1g-5.1.3.qcow2"
PACKAGE_SSH_KEY="~/.ssh/id_ed25519.pub"

# Stage outside the repo so git and the repo's own files never leak in.
STAGE_PARENT="$(mktemp -d)"
trap 'rm -rf "${STAGE_PARENT}"' EXIT
STAGE="${STAGE_PARENT}/${NAME}"

copy() {
  local src="$1" dest="${2:-$1}"
  mkdir -p "$(dirname "${STAGE}/${dest}")"
  cp "${REPO_ROOT}/${src}" "${STAGE}/${dest}"
}

echo "=== Building ${NAME} ==="

copy packaging/kvm/README.md README.md
copy project_objective/netropy-topology.svg docs/netropy-topology.svg
copy config/lab-config.schema.json

for f in "${REPO_ROOT}"/cli/netropy_lab/*.py; do
  copy "cli/netropy_lab/$(basename "${f}")"
done

for f in main.tf variables.tf outputs.tf run-apply.sh run-destroy.sh run-start.sh; do
  copy "modules/kvm/${f}"
done
for f in "${REPO_ROOT}"/modules/kvm/cloud-init/*; do
  copy "modules/kvm/cloud-init/$(basename "${f}")"
done

copy ansible/ansible.cfg
copy ansible/README.md
for f in "${REPO_ROOT}"/ansible/playbooks/*.yml; do
  copy "ansible/playbooks/$(basename "${f}")"
done

copy scripts/verify-setup.sh
copy scripts/fix-libvirt-permissions.sh

# The user-edited config: same lab values as the working config, but host-neutral paths.
mkdir -p "${STAGE}/config"
python3 - "${REPO_ROOT}/config/example-kvm.json" "${STAGE}/config/example-kvm.json" \
  "${PACKAGE_NETROPY_IMAGE}" "${PACKAGE_SSH_KEY}" <<'PY'
import json
import sys
from pathlib import Path

src, dest, netropy_image, ssh_key = sys.argv[1:5]
config = json.loads(Path(src).read_text(encoding="utf-8"))
config["netropy_image"] = netropy_image
config["ssh_public_key_file"] = ssh_key
Path(dest).write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
PY

chmod 755 "${STAGE}"/modules/kvm/*.sh "${STAGE}"/scripts/*.sh

echo "--- Safety checks ---"
FAIL=0

FORBIDDEN="$(find "${STAGE}" \( \
  -name '*.tfstate*' -o -name '*.tfvars*' -o -name '.terraform*' -o \
  -name '__pycache__' -o -name '*.pyc' -o -name '*.generated.*' -o \
  -name '*.qcow2' -o -name '*.img' -o -name '*.ova' -o -name '*.vmdk' -o -name '*.iso' -o \
  -name '*.pem' -o -name '*.key' -o -name '.env*' -o -name 'id_rsa*' -o -name 'id_ed25519*' \
  \) -print)"
if [[ -n "${FORBIDDEN}" ]]; then
  echo "  FAIL: forbidden files staged:" >&2
  echo "${FORBIDDEN}" >&2
  FAIL=1
fi

PATTERNS=(
  'BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY'
  'aws_secret_access_key|AWS_SECRET_ACCESS_KEY'
  "password\\s*[:=]\\s*[\"'][^\"']{8,}"
  '/home/[A-Za-z0-9_.-]+/'
)
for pattern in "${PATTERNS[@]}"; do
  if matches="$(grep -rlE -- "${pattern}" "${STAGE}")"; then
    echo "  FAIL: pattern '${pattern}' found in:" >&2
    echo "${matches}" >&2
    FAIL=1
  fi
done

if [[ "${FAIL}" -ne 0 ]]; then
  echo "=== Package NOT created — fix the issues above ===" >&2
  exit 1
fi
echo "  PASS: no state, images, keys, secrets, or personal home paths"

mkdir -p "${DIST_DIR}"
tar -C "${STAGE_PARENT}" --owner=0 --group=0 --numeric-owner -czf "${OUT}" "${NAME}"

echo ""
echo "=== Created ${OUT} ($(du -h "${OUT}" | cut -f1)) ==="
tar -tzf "${OUT}"
