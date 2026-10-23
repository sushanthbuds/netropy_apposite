#!/usr/bin/env bash
# Scan tracked and staged files for common secret patterns before commit.
# Exit 0 if clean; exit 1 if potential secrets found.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

FAIL=0

echo "=== Secret and sensitive file check ==="

# Files that must never be tracked
FORBIDDEN_PATHS=(
  "lab.auto.tfvars.json"
  "generated.auto.tfvars"
  ".env"
)
for path in "${FORBIDDEN_PATHS[@]}"; do
  if git ls-files --error-unmatch "${path}" >/dev/null 2>&1; then
    echo "  FAIL: tracked forbidden file: ${path}" >&2
    FAIL=1
  fi
done

# Any tfstate tracked
if git ls-files '*.tfstate' '*.tfstate.*' 2>/dev/null | grep -q .; then
  echo "  FAIL: tfstate file(s) are tracked by git:" >&2
  git ls-files '*.tfstate' '*.tfstate.*' >&2
  FAIL=1
fi

# Private key filenames tracked
if git ls-files | grep -qE '(^|/)(id_rsa|id_ed25519)(\.pub)?$'; then
  echo "  FAIL: SSH key file tracked by git" >&2
  FAIL=1
fi

# Scan staged + tracked text files for suspicious patterns (exclude binary paths)
PATTERNS=(
  'BEGIN (RSA |OPENSSH |EC )?PRIVATE KEY'
  'aws_secret_access_key'
  'AWS_SECRET_ACCESS_KEY'
  'password\s*[:=]\s*["\x27][^"\x27]{8,}'
)
SCAN_FILES=$(git ls-files 2>/dev/null | grep -v '^scripts/check-secrets.sh$' || find . -type f \
  ! -path './.git/*' \
  ! -path './images/*' \
  ! -path '*/.terraform/*' \
  ! -name '*.img' \
  ! -name '*.qcow2' \
  ! -name '*.docx' \
  ! -name '*.svg')

for pattern in "${PATTERNS[@]}"; do
  if echo "${SCAN_FILES}" | xargs grep -lE "${pattern}" 2>/dev/null | grep -q .; then
    echo "  FAIL: pattern '${pattern}' found in:" >&2
    echo "${SCAN_FILES}" | xargs grep -lE "${pattern}" 2>/dev/null >&2
    FAIL=1
  fi
done

if [[ "${FAIL}" -eq 0 ]]; then
  echo "  PASS: no forbidden tracked files or obvious secret patterns"
  exit 0
fi

echo ""
echo "Fix issues before committing. See docs/phase_2/security-guardrails.md"
exit 1
