#!/usr/bin/env bash
# Build a clean, shareable tarball of the manual ESXi demo lab: dist/netropy-esxi-demo.tar.gz
# Copies an explicit allowlist only — no rendered output, images, keys, or .git.
# Exit 0 on success; exit 1 if the staged package fails the safety checks.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAME="netropy-esxi-demo"
DIST_DIR="${REPO_ROOT}/dist"
OUT="${DIST_DIR}/${NAME}.tar.gz"

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

copy packaging/esxi/README.md README.md
copy packaging/esxi/lab-parameters.json lab-parameters.json
copy packaging/esxi/render-configs.py render-configs.py
copy project_objective/netropy-topology.svg docs/netropy-topology.svg

chmod 755 "${STAGE}/render-configs.py"

echo "--- Safety checks ---"
FAIL=0

if ! python3 "${STAGE}/render-configs.py" -o "${STAGE_PARENT}/render-check" >/dev/null; then
  echo "  FAIL: render-configs.py rejects the packaged lab-parameters.json" >&2
  FAIL=1
fi

FORBIDDEN="$(find "${STAGE}" \( \
  -name 'output' -o -name '__pycache__' -o -name '*.pyc' -o \
  -name '*.ova' -o -name '*.ovf' -o -name '*.vmdk' -o -name '*.iso' -o -name '*.qcow2' -o \
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
  'sushanth'
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
echo "  PASS: parameters render; no images, keys, secrets, or personal names/paths"

mkdir -p "${DIST_DIR}"
tar -C "${STAGE_PARENT}" --owner=0 --group=0 --numeric-owner -czf "${OUT}" "${NAME}"

echo ""
echo "=== Created ${OUT} ($(du -h "${OUT}" | cut -f1)) ==="
tar -tzf "${OUT}"
