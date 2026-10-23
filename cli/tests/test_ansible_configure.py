"""Tests for Ansible inventory helper and configure CLI command."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from netropy_lab.ansible_inv import build_inventory_ini, write_inventory
from netropy_lab.cli import cmd_configure


SAMPLE_CONFIG = {
    "platform": "kvm",
    "subnets": {
        "mgmt": {"cidr": "192.168.100.0/24"},
        "data1": {"cidr": "192.168.101.0/24"},
        "data2": {"cidr": "192.168.102.0/24"},
    },
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


def test_build_inventory_ini_maps_peer_subnets() -> None:
    text = build_inventory_ini(SAMPLE_CONFIG)
    assert "linux1 ansible_host=192.168.100.21" in text
    assert "linux2 ansible_host=192.168.100.22" in text
    assert "peer_data_cidr=192.168.102.0/24" in text  # linux1 peers to data2
    assert "peer_data_cidr=192.168.101.0/24" in text  # linux2 peers to data1
    assert "peer_data_ip=192.168.102.22" in text
    assert "peer_data_ip=192.168.101.21" in text
    assert "ansible_user=ubuntu" in text


def test_write_inventory_creates_file(tmp_path: Path) -> None:
    dest = tmp_path / "inventory" / "lab.generated.ini"
    path = write_inventory(SAMPLE_CONFIG, dest)
    assert path == dest
    assert dest.is_file()
    assert "linux_endpoints" in dest.read_text(encoding="utf-8")


def _args(config: Path) -> MagicMock:
    return MagicMock(config=str(config))


@patch("netropy_lab.cli.subprocess.run")
@patch("netropy_lab.cli.write_inventory")
@patch("netropy_lab.cli.shutil.which", return_value="/usr/bin/ansible-playbook")
@patch("netropy_lab.cli.validate_config")
def test_cmd_configure_runs_ansible(
    validate: MagicMock,
    _which: MagicMock,
    write_inv: MagicMock,
    run: MagicMock,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "lab.json"
    validate.return_value = SAMPLE_CONFIG
    inv_path = tmp_path / "lab.generated.ini"
    write_inv.return_value = inv_path
    run.return_value = MagicMock(returncode=0)

    with patch("netropy_lab.cli.ANSIBLE_PLAYBOOK", tmp_path / "configure-routes.yml"):
        (tmp_path / "configure-routes.yml").write_text("---\n", encoding="utf-8")
        rc = cmd_configure(_args(config_path))

    assert rc == 0
    write_inv.assert_called_once()
    run.assert_called_once()
    cmd = run.call_args[0][0]
    assert cmd[0] == "/usr/bin/ansible-playbook"
    assert "-i" in cmd
    assert str(inv_path) in cmd


@patch("netropy_lab.cli.shutil.which", return_value=None)
@patch("netropy_lab.cli.validate_config")
def test_cmd_configure_requires_ansible(
    validate: MagicMock,
    _which: MagicMock,
    tmp_path: Path,
) -> None:
    config_path = tmp_path / "lab.json"
    validate.return_value = SAMPLE_CONFIG
    rc = cmd_configure(_args(config_path))
    assert rc == 1


@patch("netropy_lab.cli.validate_config")
def test_cmd_configure_rejects_unsupported_platform(validate: MagicMock, tmp_path: Path) -> None:
    config_path = tmp_path / "lab.json"
    validate.return_value = {**SAMPLE_CONFIG, "platform": "esxi"}
    rc = cmd_configure(_args(config_path))
    assert rc == 1
