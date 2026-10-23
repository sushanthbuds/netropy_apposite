"""Unit tests for KVM/libvirt CLI helpers (Phase 6)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from netropy_lab import kvm
from netropy_lab.validator import ConfigError


def test_ensure_not_root_rejects_root() -> None:
    with patch.object(kvm.os, "geteuid", return_value=0):
        with pytest.raises(ConfigError, match="Do not run"):
            kvm.ensure_not_root()


def test_ensure_libvirt_group_requires_membership() -> None:
    with patch.object(kvm, "can_access_libvirt", return_value=False):
        with patch.object(kvm, "user_in_libvirt_group", return_value=False):
            with pytest.raises(ConfigError, match="libvirt group"):
                kvm.ensure_libvirt_group()


def test_ensure_libvirt_group_allows_sg_libvirt_access() -> None:
    with patch.object(kvm, "can_access_libvirt", return_value=True):
        kvm.ensure_libvirt_group()


def test_run_tofu_uses_sg_libvirt() -> None:
    module_dir = Path("/tmp/kvm-module")
    with patch.object(kvm, "ensure_not_root"):
        with patch.object(kvm, "ensure_libvirt_group"):
            with patch.object(kvm.subprocess, "run", return_value=MagicMock(returncode=0)) as run:
                rc = kvm.run_tofu(module_dir, "apply")
    assert rc == 0
    run.assert_called_once()
    args, kwargs = run.call_args
    assert args[0] == ["sg", "libvirt", "-c", "tofu init -upgrade && tofu apply -auto-approve"]
    assert kwargs["cwd"] == module_dir


def test_run_tofu_plan_has_no_auto_approve() -> None:
    module_dir = Path("/tmp/kvm-module")
    with patch.object(kvm, "ensure_not_root"):
        with patch.object(kvm, "ensure_libvirt_group"):
            with patch.object(kvm.subprocess, "run", return_value=MagicMock(returncode=0)) as run:
                kvm.run_tofu(module_dir, "plan")
    args, _ = run.call_args
    assert args[0][3] == "tofu init -upgrade && tofu plan"


def test_lab_vm_names_includes_netropy_when_enabled() -> None:
    names = kvm.lab_vm_names("netropy-lab", provision_netropy=True)
    assert names == ["netropy-lab-linux1", "netropy-lab-linux2", "netropy-lab-netropy"]


def test_lab_vm_names_skips_netropy_when_disabled() -> None:
    names = kvm.lab_vm_names("netropy-lab", provision_netropy=False)
    assert names == ["netropy-lab-linux1", "netropy-lab-linux2"]


def test_confirm_destroy_aborts_without_yes() -> None:
    with patch.dict(kvm.os.environ, {}, clear=True):
        with patch("builtins.input", return_value="no"):
            with pytest.raises(ConfigError, match="aborted"):
                kvm.confirm_destroy(force=False)


def test_confirm_destroy_skips_prompt_when_forced() -> None:
    with patch("builtins.input") as input_mock:
        kvm.confirm_destroy(force=True)
    input_mock.assert_not_called()


def test_run_virsh_uses_direct_when_successful() -> None:
    with patch.object(kvm.subprocess, "run", return_value=MagicMock(returncode=0)) as run:
        kvm.run_virsh("list", "--all")
    run.assert_called_once()
    args, _ = run.call_args
    assert args[0][:3] == ["virsh", "-c", kvm.VIRSH_URI]


def test_run_virsh_falls_back_to_sg_libvirt() -> None:
    direct = MagicMock(returncode=1)
    fallback = MagicMock(returncode=0)
    with patch.object(kvm.subprocess, "run", side_effect=[direct, fallback]) as run:
        result = kvm.run_virsh("domstate", "netropy-lab-linux1")
    assert result.returncode == 0
    assert run.call_count == 2
    second_args, _ = run.call_args_list[1]
    assert second_args[0][0] == "sg"
