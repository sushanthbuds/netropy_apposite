"""CLI command tests for Phase 6 up/plan/down."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from netropy_lab.cli import cmd_down, cmd_plan, cmd_up


def _args(config: Path, **extra: object) -> MagicMock:
    payload = {"config": str(config), **extra}
    return MagicMock(**payload)


@patch("netropy_lab.cli._kvm_post_apply")
@patch("netropy_lab.cli._run_platform_tofu", return_value=0)
@patch("netropy_lab.cli._prepare_tfvars")
@patch("netropy_lab.cli.validate_config")
@patch("netropy_lab.kvm.ensure_pool")
@patch("netropy_lab.kvm.ensure_libvirt_group")
@patch("netropy_lab.kvm.ensure_not_root")
def test_cmd_up_runs_kvm_flow(
    _not_root: MagicMock,
    _libvirt: MagicMock,
    _pool: MagicMock,
    validate: MagicMock,
    prepare: MagicMock,
    run_tofu: MagicMock,
    post_apply: MagicMock,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "lab.json"
    config_path.write_text("{}", encoding="utf-8")
    validate.return_value = {
        "platform": "kvm",
        "naming_prefix": "netropy-lab",
        "options": {"provision_netropy": True},
        "instances": {
            "linux1": {"mgmt_ip": "192.168.100.21", "data_ip": "192.168.101.21"},
            "linux2": {"mgmt_ip": "192.168.100.22", "data_ip": "192.168.102.22"},
            "netropy": {
                "mgmt_ip": "192.168.100.10",
                "data1_ip": "192.168.101.10",
                "data2_ip": "192.168.102.10",
            },
        },
    }

    rc = cmd_up(_args(config_path))

    assert rc == 0
    prepare.assert_called_once()
    run_tofu.assert_called_once()
    post_apply.assert_called_once()


@patch("netropy_lab.cli._run_platform_tofu", return_value=0)
@patch("netropy_lab.cli._prepare_tfvars")
@patch("netropy_lab.cli.validate_config")
@patch("netropy_lab.cli._kvm_preflight")
def test_cmd_plan_calls_tofu_plan(
    preflight: MagicMock,
    validate: MagicMock,
    prepare: MagicMock,
    run_tofu: MagicMock,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "lab.json"
    validate.return_value = {"platform": "kvm"}

    rc = cmd_plan(_args(config_path))

    assert rc == 0
    prepare.assert_called_once()
    run_tofu.assert_called_once()
    assert run_tofu.call_args[0][2] == "plan"


@patch("netropy_lab.cli._run_platform_tofu", return_value=0)
@patch("netropy_lab.kvm.confirm_destroy")
@patch("netropy_lab.cli._kvm_preflight")
@patch("netropy_lab.cli.validate_config")
def test_cmd_down_confirms_before_destroy(
    validate: MagicMock,
    preflight: MagicMock,
    confirm: MagicMock,
    run_tofu: MagicMock,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "lab.json"
    validate.return_value = {"platform": "kvm"}

    rc = cmd_down(_args(config_path, yes=False))

    assert rc == 0
    preflight.assert_called_once()
    confirm.assert_called_once_with(force=False)
    run_tofu.assert_called_once()
    assert run_tofu.call_args[0][2] == "destroy"
