"""Lab health checks for the verify command (Phase 7)."""

from __future__ import annotations

import json
import subprocess
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Protocol

from netropy_lab import kvm

PING_COUNT = 2
PING_TIMEOUT_SEC = 2
SSH_TIMEOUT_SEC = 20


class CheckStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_READY = "NOT READY"


@dataclass(frozen=True)
class CheckResult:
    layer: str
    name: str
    status: CheckStatus
    detail: str
    hint: str = ""

    def to_dict(self) -> dict[str, str]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload


class CommandRunner(Protocol):
    def __call__(
        self,
        args: list[str],
        *,
        timeout: int | None = None,
    ) -> subprocess.CompletedProcess[str]: ...


def default_runner(
    args: list[str],
    *,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        check=False,
        timeout=timeout,
        capture_output=True,
        text=True,
    )


def resolve_ssh_private_key(ssh_public_key_file: str | None) -> Path | None:
    """Map JSON ssh_public_key_file (*.pub) to the matching private key if present."""
    if not ssh_public_key_file:
        return None
    pub = Path(ssh_public_key_file).expanduser()
    if pub.name.endswith(".pub"):
        private = pub.with_suffix("")
    else:
        private = pub
    if private.is_file():
        return private
    return None


def _lab_network_names(prefix: str) -> list[str]:
    return [f"{prefix}-mgmt", f"{prefix}-data1", f"{prefix}-data2"]


def _ping_ok(host: str, run: CommandRunner) -> bool:
    result = run(
        [
            "ping",
            "-c",
            str(PING_COUNT),
            "-W",
            str(PING_TIMEOUT_SEC),
            host,
        ],
        timeout=PING_TIMEOUT_SEC * PING_COUNT + 5,
    )
    return result.returncode == 0


def _ssh_batch(
    user_host: str,
    remote_cmd: str,
    run: CommandRunner,
    *,
    timeout: int = SSH_TIMEOUT_SEC,
    identity_file: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    args = [
        "ssh",
        "-o",
        "BatchMode=yes",
        "-o",
        "ConnectTimeout=5",
        "-o",
        "StrictHostKeyChecking=accept-new",
    ]
    if identity_file is not None:
        args.extend(
            [
                "-i",
                str(identity_file),
                "-o",
                "IdentitiesOnly=yes",
            ]
        )
    args.extend([user_host, remote_cmd])
    return run(args, timeout=timeout)


def _http_reachable(url: str, timeout: int = 5) -> tuple[bool, str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return True, f"HTTP {response.status}"
    except urllib.error.HTTPError as exc:
        if exc.code in (301, 302, 401, 403):
            return True, f"HTTP {exc.code}"
        return False, f"HTTP {exc.code}"
    except Exception as exc:  # noqa: BLE001 — surface network errors to the user
        return False, str(exc)


def _count_xml_interfaces(dumpxml: str) -> int:
    return dumpxml.count("<interface ")


def verify_kvm_lab(
    config: dict[str, Any],
    *,
    run: CommandRunner | None = None,
) -> list[CheckResult]:
    """Run layered KVM lab checks. Does not provision or mutate the lab."""
    runner = run or default_runner
    prefix = config.get("naming_prefix", "netropy-lab")
    instances = config["instances"]
    provision_netropy = config.get("options", {}).get("provision_netropy", True)
    identity = resolve_ssh_private_key(config.get("ssh_public_key_file"))
    vm_names = kvm.lab_vm_names(prefix, provision_netropy=provision_netropy)
    expected_ifaces = {
        f"{prefix}-linux1": 2,
        f"{prefix}-linux2": 2,
        f"{prefix}-netropy": 3,
    }
    results: list[CheckResult] = []

    net_list = kvm.run_virsh("net-list", "--name")
    active_nets = {line.strip() for line in (net_list.stdout or "").splitlines() if line.strip()}
    for net in _lab_network_names(prefix):
        if net in active_nets:
            results.append(
                CheckResult("libvirt", f"network {net}", CheckStatus.PASS, "active")
            )
        else:
            results.append(
                CheckResult(
                    "libvirt",
                    f"network {net}",
                    CheckStatus.FAIL,
                    "not found",
                    hint="Run: PYTHONPATH=cli python3 -m netropy_lab.cli up -c <config>",
                )
            )

    for vm in vm_names:
        state = kvm.run_virsh("domstate", vm)
        if state.returncode != 0:
            results.append(
                CheckResult(
                    "libvirt",
                    f"domain {vm}",
                    CheckStatus.FAIL,
                    "not defined",
                    hint="Run: PYTHONPATH=cli python3 -m netropy_lab.cli up -c <config>",
                )
            )
            continue

        current = (state.stdout or "").strip()
        if current == "running":
            results.append(
                CheckResult("libvirt", f"domain {vm}", CheckStatus.PASS, "running")
            )
        else:
            results.append(
                CheckResult(
                    "libvirt",
                    f"domain {vm}",
                    CheckStatus.FAIL,
                    f"state is {current or 'unknown'}",
                    hint=f"Run: virsh -c {kvm.VIRSH_URI} start {vm}",
                )
            )

        if vm not in expected_ifaces:
            continue

        xml = kvm.run_virsh("dumpxml", vm)
        if xml.returncode != 0:
            results.append(
                CheckResult(
                    "libvirt",
                    f"{vm} NIC count",
                    CheckStatus.FAIL,
                    "could not read domain XML",
                )
            )
            continue

        count = _count_xml_interfaces(xml.stdout or "")
        expected = expected_ifaces[vm]
        if count == expected:
            results.append(
                CheckResult(
                    "libvirt",
                    f"{vm} NIC count",
                    CheckStatus.PASS,
                    f"{count} interfaces",
                )
            )
        else:
            results.append(
                CheckResult(
                    "libvirt",
                    f"{vm} NIC count",
                    CheckStatus.FAIL,
                    f"expected {expected}, found {count}",
                    hint="Re-apply the KVM module or inspect virsh dumpxml",
                )
            )

    mgmt_targets = [
        ("linux1 mgmt", instances["linux1"]["mgmt_ip"]),
        ("linux2 mgmt", instances["linux2"]["mgmt_ip"]),
    ]
    if provision_netropy:
        mgmt_targets.append(("netropy mgmt", instances["netropy"]["mgmt_ip"]))

    for label, ip in mgmt_targets:
        if _ping_ok(ip, runner):
            results.append(
                CheckResult("management", f"ping {label}", CheckStatus.PASS, ip)
            )
        else:
            results.append(
                CheckResult(
                    "management",
                    f"ping {label}",
                    CheckStatus.FAIL,
                    f"no reply from {ip}",
                    hint="Wait for boot/cloud-init or check virsh domstate",
                )
            )

    if provision_netropy:
        ok, detail = _http_reachable(f"http://{instances['netropy']['mgmt_ip']}/")
        if ok:
            results.append(
                CheckResult("management", "netropy web UI", CheckStatus.PASS, detail)
            )
        else:
            results.append(
                CheckResult(
                    "management",
                    "netropy web UI",
                    CheckStatus.NOT_READY,
                    detail,
                    hint="On Netropy CLI run: http on",
                )
            )

    linux_checks: list[tuple[str, str, str, str]] = [
        (
            "linux1",
            instances["linux1"]["mgmt_ip"],
            instances["linux1"]["data_ip"],
            instances["linux2"]["data_ip"],
        ),
        (
            "linux2",
            instances["linux2"]["mgmt_ip"],
            instances["linux2"]["data_ip"],
            instances["linux1"]["data_ip"],
        ),
    ]

    for host_label, mgmt_ip, data_ip, peer_data_ip in linux_checks:
        ssh_target = f"ubuntu@{mgmt_ip}"
        ssh_probe = _ssh_batch(ssh_target, "true", runner, identity_file=identity)
        if ssh_probe.returncode != 0:
            results.append(
                CheckResult(
                    "linux-guest",
                    f"{host_label} SSH",
                    CheckStatus.FAIL,
                    "key-based SSH failed",
                    hint="Confirm ssh_public_key_file in JSON matches this host",
                )
            )
            continue

        results.append(
            CheckResult("linux-guest", f"{host_label} SSH", CheckStatus.PASS, ssh_target)
        )

        ci = _ssh_batch(
            ssh_target,
            "cloud-init status 2>/dev/null || true",
            runner,
            identity_file=identity,
        )
        ci_text = (ci.stdout or ci.stderr or "").strip()
        if "status: done" in ci_text:
            results.append(
                CheckResult(
                    "linux-guest",
                    f"{host_label} cloud-init",
                    CheckStatus.PASS,
                    "done",
                )
            )
        elif ci_text:
            results.append(
                CheckResult(
                    "linux-guest",
                    f"{host_label} cloud-init",
                    CheckStatus.NOT_READY,
                    ci_text.splitlines()[-1],
                    hint="Wait ~90s after up, then re-run verify",
                )
            )
        else:
            results.append(
                CheckResult(
                    "linux-guest",
                    f"{host_label} cloud-init",
                    CheckStatus.NOT_READY,
                    "status unavailable",
                    hint="Wait ~90s after up, then re-run verify",
                )
            )

        addr = _ssh_batch(
            ssh_target, "ip -br addr", runner, identity_file=identity
        )
        addr_text = addr.stdout or ""
        if data_ip in addr_text and mgmt_ip in addr_text:
            results.append(
                CheckResult(
                    "linux-guest",
                    f"{host_label} addresses",
                    CheckStatus.PASS,
                    f"mgmt {mgmt_ip}, data {data_ip}",
                )
            )
        else:
            results.append(
                CheckResult(
                    "linux-guest",
                    f"{host_label} addresses",
                    CheckStatus.FAIL,
                    "expected IPs not found on guest",
                    hint=f"Inspect: ssh ubuntu@{mgmt_ip} ip -br addr",
                )
            )

        iperf = _ssh_batch(
            ssh_target,
            "iperf3 --version 2>/dev/null | head -1",
            runner,
            identity_file=identity,
        )
        if iperf.returncode == 0 and (iperf.stdout or "").strip():
            results.append(
                CheckResult(
                    "linux-guest",
                    f"{host_label} iperf3",
                    CheckStatus.PASS,
                    (iperf.stdout or "").strip(),
                )
            )
        else:
            results.append(
                CheckResult(
                    "linux-guest",
                    f"{host_label} iperf3",
                    CheckStatus.FAIL,
                    "not installed",
                    hint="Re-run up or inspect cloud-init user-data",
                )
            )

        peer_ping = _ssh_batch(
            ssh_target,
            f"ping -c {PING_COUNT} -W {PING_TIMEOUT_SEC} {peer_data_ip}",
            runner,
            timeout=PING_TIMEOUT_SEC * PING_COUNT + 10,
            identity_file=identity,
        )
        if peer_ping.returncode == 0:
            results.append(
                CheckResult(
                    "data-path",
                    f"{host_label} -> peer data",
                    CheckStatus.PASS,
                    peer_data_ip,
                )
            )
        else:
            results.append(
        CheckResult(
                    "data-path",
                    f"{host_label} -> peer data",
            CheckStatus.NOT_READY,
                    f"no reply from {peer_data_ip}",
                    hint=(
                        "Set Netropy Bridge mode and add on-link data routes "
                        "(see docs/phase_5/phase5-development-guide.md)"
                    ),
                )
            )

    return results


def summarize_checks(results: list[CheckResult]) -> dict[str, CheckStatus]:
    infra_layers = {"libvirt", "management", "linux-guest"}
    infra = [r for r in results if r.layer in infra_layers]
    forwarding = [r for r in results if r.layer == "data-path"]

    def _rollup(checks: list[CheckResult]) -> CheckStatus:
        if not checks:
            return CheckStatus.NOT_READY
        if any(c.status == CheckStatus.FAIL for c in checks):
            return CheckStatus.FAIL
        if any(c.status == CheckStatus.NOT_READY for c in checks):
            return CheckStatus.NOT_READY
        return CheckStatus.PASS

    return {
        "infrastructure": _rollup(infra),
        "netropy_forwarding": _rollup(forwarding),
    }



def format_verify_report(
    results: list[CheckResult],
    *,
    config_path: str | None = None,
) -> str:
    summary = summarize_checks(results)
    lines = ["=== Netropy Lab Verify ===", ""]
    if config_path:
        lines.append(f"Config: {config_path}")
        lines.append("")

    current_layer = ""
    for check in results:
        if check.layer != current_layer:
            current_layer = check.layer
            lines.append(f"Layer: {current_layer}")
        lines.append(f"  [{check.status.value}] {check.name}: {check.detail}")
        if check.hint and check.status != CheckStatus.PASS:
            lines.append(f"           -> {check.hint}")

    lines.extend(
        [
            "",
            "=== Summary ===",
            f"Infrastructure:      {summary['infrastructure'].value}",
            f"Netropy forwarding:  {summary['netropy_forwarding'].value}",
            "",
        ]
    )
    return "\n".join(lines)


def write_failure_bundle(
    path: Path,
    *,
    config_path: Path,
    results: list[CheckResult],
) -> None:
    summary = summarize_checks(results)
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "config": str(config_path),
        "summary": {key: value.value for key, value in summary.items()},
        "checks": [check.to_dict() for check in results],
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def exit_code_for_results(
    results: list[CheckResult],
    *,
    require_forwarding: bool = False,
) -> int:
    summary = summarize_checks(results)
    if summary["infrastructure"] == CheckStatus.FAIL:
        return 1
    if any(r.status == CheckStatus.FAIL for r in results):
        return 1
    if require_forwarding and summary["netropy_forwarding"] != CheckStatus.PASS:
        return 1
    return 0
