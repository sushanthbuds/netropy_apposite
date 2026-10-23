"""Unit tests for Phase 7 verify command."""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

import pytest

from netropy_lab.cli import cmd_verify
from netropy_lab.verify import (
    CheckResult,
    CheckStatus,
    exit_code_for_results,
    format_verify_report,
    summarize_checks,
    verify_kvm_lab,
    write_failure_bundle,
)

SAMPLE_CONFIG = {
    "platform": "kvm",
    "naming_prefix": "netropy-lab",
    "options": {"provision_netropy": True},
    "instances": {
        "netropy": {
            "mgmt_ip": "192.168.100.10",
            "data1_ip": "192.168.101.10",
            "data2_ip": "192.168.102.10",
        },
        "linux1": {
            "mgmt_ip": "192.168.100.21",
            "data_ip": "192.168.101.21",
        },
        "linux2": {
            "mgmt_ip": "192.168.100.22",
            "data_ip": "192.168.102.22",
        },
    },
}


def _completed(stdout: str = "", returncode: int = 0) -> subprocess.CompletedProcess[str]:
    return subprocess.CompletedProcess(
        args=[],
        returncode=returncode,
        stdout=stdout,
        stderr="",
    )


def _happy_virsh(*args: str) -> subprocess.CompletedProcess[str]:
    if args[:2] == ("net-list", "--name"):
        return _completed(
            "netropy-lab-mgmt\nnetropy-lab-data1\nnetropy-lab-data2\n"
        )
    if len(args) == 2 and args[0] == "domstate":
        return _completed("running\n")
    if len(args) == 2 and args[0] == "dumpxml":
        vm = args[1]
        count = 3 if vm.endswith("-netropy") else 2
        return _completed("<interface type='network'></interface>\n" * count)
    return _completed("", returncode=1)


def _happy_runner(args: list[str], *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
    joined = " ".join(args)
    remote_cmd = args[-1] if args else ""
    if joined.startswith("ping "):
        return _completed("bytes from")
    if remote_cmd == "true":
        return _completed("")
    if "cloud-init status" in remote_cmd:
        return _completed("status: done\n")
    if remote_cmd == "ip -br addr":
        if "192.168.100.21" in joined:
            return _completed(
                "eth0  UP  192.168.100.21/24\neth1  UP  192.168.101.21/24\n"
            )
        return _completed(
            "eth0  UP  192.168.100.22/24\neth1  UP  192.168.102.22/24\n"
        )
    if "iperf3 --version" in remote_cmd:
        return _completed("iperf 3.16 (cJSON 1.7.15)\n")
    if remote_cmd.startswith("ping -c") and "192.168.102.22" in remote_cmd:
        return _completed("bytes from 192.168.102.22")
    if remote_cmd.startswith("ping -c") and "192.168.101.21" in remote_cmd:
        return _completed("bytes from 192.168.101.21")
    return _completed("", returncode=1)


@patch("netropy_lab.verify._http_reachable", return_value=(True, "HTTP 302"))
@patch("netropy_lab.verify.kvm.run_virsh", side_effect=_happy_virsh)
def test_verify_kvm_lab_all_pass(_virsh, _http) -> None:
    results = verify_kvm_lab(SAMPLE_CONFIG, run=_happy_runner)
    assert all(r.status == CheckStatus.PASS for r in results)
    summary = summarize_checks(results)
    assert summary["infrastructure"] == CheckStatus.PASS
    assert summary["netropy_forwarding"] == CheckStatus.PASS


@patch("netropy_lab.verify.kvm.run_virsh")
def test_verify_kvm_lab_missing_network_fails(virsh_mock) -> None:
    virsh_mock.side_effect = lambda *args: _completed("netropy-lab-mgmt\n")
    results = verify_kvm_lab(SAMPLE_CONFIG, run=_happy_runner)
    failed = [r for r in results if r.status == CheckStatus.FAIL]
    assert any("network netropy-lab-data1" in r.name for r in failed)
    assert summarize_checks(results)["infrastructure"] == CheckStatus.FAIL


@patch("netropy_lab.verify.kvm.run_virsh")
def test_verify_kvm_lab_stopped_vm_fails(virsh_mock) -> None:
    def virsh(*args: str) -> subprocess.CompletedProcess[str]:
        if args[:2] == ("net-list", "--name"):
            return _completed(
                "netropy-lab-mgmt\nnetropy-lab-data1\nnetropy-lab-data2\n"
            )
        if len(args) == 2 and args[0] == "domstate" and args[1] == "netropy-lab-linux1":
            return _completed("shut off\n")
        return _happy_virsh(*args)

    virsh_mock.side_effect = virsh
    results = verify_kvm_lab(SAMPLE_CONFIG, run=_happy_runner)
    assert any(
        r.name == "domain netropy-lab-linux1" and r.status == CheckStatus.FAIL
        for r in results
    )


@patch("netropy_lab.verify._http_reachable", return_value=(True, "HTTP 302"))
@patch("netropy_lab.verify.kvm.run_virsh", side_effect=_happy_virsh)
def test_data_path_not_ready_without_forwarding(_virsh, _http) -> None:
    def no_peer_ping(args: list[str], *, timeout: int | None = None) -> subprocess.CompletedProcess[str]:
        remote_cmd = args[-1] if args else ""
        if remote_cmd.startswith("ping -c") and (
            "192.168.102.22" in remote_cmd or "192.168.101.21" in remote_cmd
        ):
            return _completed("", returncode=1)
        return _happy_runner(args, timeout=timeout)

    results = verify_kvm_lab(SAMPLE_CONFIG, run=no_peer_ping)
    forwarding = [r for r in results if r.layer == "data-path"]
    assert forwarding
    assert all(r.status == CheckStatus.NOT_READY for r in forwarding)
    assert exit_code_for_results(results) == 0
    assert exit_code_for_results(results, require_forwarding=True) == 1


def test_format_verify_report_includes_summary() -> None:
    results = [
        CheckResult("libvirt", "network netropy-lab-mgmt", CheckStatus.PASS, "active"),
        CheckResult(
            "data-path",
            "linux1 -> peer data",
            CheckStatus.NOT_READY,
            "no reply",
            hint="configure bridge",
        ),
    ]
    report = format_verify_report(results, config_path="config/example-kvm.json")
    assert "=== Netropy Lab Verify ===" in report
    assert "Infrastructure:" in report
    assert "Netropy forwarding:" in report
    assert "configure bridge" in report


def test_write_failure_bundle(tmp_path) -> None:
    results = [
        CheckResult("libvirt", "network netropy-lab-mgmt", CheckStatus.FAIL, "missing"),
    ]
    bundle_path = tmp_path / "verify-fail.json"
    write_failure_bundle(
        bundle_path,
        config_path=tmp_path / "lab.json",
        results=results,
    )
    payload = json.loads(bundle_path.read_text(encoding="utf-8"))
    assert payload["summary"]["infrastructure"] == "FAIL"
    assert payload["checks"][0]["name"] == "network netropy-lab-mgmt"


@patch("netropy_lab.cli.verify_kvm_lab")
@patch("netropy_lab.cli.validate_config")
@patch("netropy_lab.kvm.ensure_libvirt_group")
@patch("netropy_lab.kvm.ensure_not_root")
def test_cmd_verify_writes_bundle_on_failure(_nr, _lg, validate, verify_lab, tmp_path) -> None:
    config_path = tmp_path / "lab.json"
    config_path.write_text("{}", encoding="utf-8")
    bundle_path = tmp_path / "bundle.json"
    validate.return_value = {"platform": "kvm"}
    verify_lab.return_value = [
        CheckResult("libvirt", "network netropy-lab-mgmt", CheckStatus.FAIL, "missing"),
    ]
    args = MagicMock(
        config=str(config_path),
        require_forwarding=False,
        bundle=str(bundle_path),
    )
    assert cmd_verify(args) == 1
    assert bundle_path.exists()


@patch("netropy_lab.cli.verify_kvm_lab")
@patch("netropy_lab.cli.validate_config")
@patch("netropy_lab.kvm.ensure_libvirt_group")
@patch("netropy_lab.kvm.ensure_not_root")
def test_cmd_verify_skips_bundle_on_success(_nr, _lg, validate, verify_lab, tmp_path) -> None:
    config_path = tmp_path / "lab.json"
    config_path.write_text("{}", encoding="utf-8")
    bundle_path = tmp_path / "bundle.json"
    validate.return_value = {"platform": "kvm"}
    verify_lab.return_value = [
        CheckResult("libvirt", "network netropy-lab-mgmt", CheckStatus.PASS, "active"),
    ]
    args = MagicMock(
        config=str(config_path),
        require_forwarding=False,
        bundle=str(bundle_path),
    )
    assert cmd_verify(args) == 0
    assert not bundle_path.exists()


def test_resolve_ssh_private_key(tmp_path) -> None:
    from netropy_lab.verify import resolve_ssh_private_key

    pub = tmp_path / "id_ed25519.pub"
    priv = tmp_path / "id_ed25519"
    pub.write_text("ssh-ed25519 AAAA test\n", encoding="utf-8")
    priv.write_text("PRIVATE\n", encoding="utf-8")
    assert resolve_ssh_private_key(str(pub)) == priv
    assert resolve_ssh_private_key(str(tmp_path / "missing.pub")) is None
