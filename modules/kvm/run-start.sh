#!/usr/bin/env bash
# Start stopped lab VMs without re-running OpenTofu apply.
set -euo pipefail

for vm in netropy-lab-linux1 netropy-lab-linux2 netropy-lab-netropy; do
  if ! virsh -c qemu:///system dominfo "${vm}" >/dev/null 2>&1; then
    echo "${vm}: not found — run ./run-apply.sh first" >&2
    continue
  fi
  virsh -c qemu:///system autostart "${vm}" >/dev/null
  state="$(virsh -c qemu:///system domstate "${vm}")"
  if [[ "${state}" == "running" ]]; then
    echo "${vm}: already running"
    continue
  fi
  virsh -c qemu:///system start "${vm}"
  virsh -c qemu:///system qemu-monitor-command "${vm}" --hmp cont >/dev/null 2>&1 || true
  echo "${vm}: started"
done
