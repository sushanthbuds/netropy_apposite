"""Unit tests for OpenTofu tfvars generation (Phase 6)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from netropy_lab.tfvars import (
    DEFAULT_NETROPY_CONFIG_DISK_NAME,
    DEFAULT_UBUNTU_IMAGE,
    build_tfvars_payload,
    resolve_netropy_config_image,
    write_tfvars,
)
from netropy_lab.validator import ConfigError


def _base_config(tmp_path: Path, *, provision_netropy: bool = True) -> dict:
    ssh_key = tmp_path / "id_ed25519.pub"
    ssh_key.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAtest test@host\n", encoding="utf-8")
    netropy_dir = tmp_path / "Netropy-VM"
    netropy_dir.mkdir()
    disk1 = netropy_dir / "vn-disk1g-5.1.3.qcow2"
    disk1.write_text("disk1", encoding="utf-8")
    if provision_netropy:
        (netropy_dir / DEFAULT_NETROPY_CONFIG_DISK_NAME).write_text("disk2", encoding="utf-8")
    return {
        "platform": "kvm",
        "naming_prefix": "netropy-lab",
        "ssh_public_key_file": str(ssh_key),
        "netropy_image": str(disk1),
        "subnets": {
            "mgmt": {"cidr": "192.168.100.0/24"},
            "data1": {"cidr": "192.168.101.0/24"},
            "data2": {"cidr": "192.168.102.0/24"},
        },
        "instances": {
            "netropy": {
                "mgmt_ip": "192.168.100.10",
                "data1_ip": "192.168.101.10",
                "data2_ip": "192.168.102.10",
            },
            "linux1": {"mgmt_ip": "192.168.100.21", "data_ip": "192.168.101.21"},
            "linux2": {"mgmt_ip": "192.168.100.22", "data_ip": "192.168.102.22"},
        },
        "options": {"provision_netropy": provision_netropy},
    }


def test_resolve_netropy_config_image_from_sibling(tmp_path: Path) -> None:
    config = _base_config(tmp_path)
    expected = str((tmp_path / "Netropy-VM" / DEFAULT_NETROPY_CONFIG_DISK_NAME).resolve())
    assert resolve_netropy_config_image(config) == expected


def test_resolve_netropy_config_image_explicit(tmp_path: Path) -> None:
    config = _base_config(tmp_path)
    explicit = tmp_path / "custom-config.qcow2"
    explicit.write_text("cfg", encoding="utf-8")
    config["netropy_config_image"] = str(explicit)
    assert resolve_netropy_config_image(config) == str(explicit.resolve())


def test_build_tfvars_payload_includes_host_paths(tmp_path: Path) -> None:
    config = _base_config(tmp_path)
    payload = build_tfvars_payload(config)

    assert payload["ubuntu_image"] == str(DEFAULT_UBUNTU_IMAGE)
    assert payload["netropy_config_image"] == resolve_netropy_config_image(config)
    assert payload["ssh_public_key"].startswith("ssh-ed25519")
    assert payload["naming_prefix"] == "netropy-lab"


def test_build_tfvars_payload_missing_config_disk_raises(tmp_path: Path) -> None:
    config = _base_config(tmp_path, provision_netropy=True)
    (tmp_path / "Netropy-VM" / DEFAULT_NETROPY_CONFIG_DISK_NAME).unlink()

    with pytest.raises(ConfigError, match="netropy_config_image missing"):
        build_tfvars_payload(config)


def test_build_tfvars_payload_skips_config_disk_when_netropy_disabled(tmp_path: Path) -> None:
    config = _base_config(tmp_path, provision_netropy=False)

    payload = build_tfvars_payload(config)
    assert payload["netropy_config_image"] == ""


def test_write_tfvars_writes_json(tmp_path: Path) -> None:
    config = _base_config(tmp_path)
    dest = tmp_path / "lab.auto.tfvars.json"
    write_tfvars(config, dest)

    written = json.loads(dest.read_text(encoding="utf-8"))
    assert written["ubuntu_image"] == str(DEFAULT_UBUNTU_IMAGE)
    assert written["netropy_config_image"]
