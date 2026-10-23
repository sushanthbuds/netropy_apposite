"""Unit tests for Phase 4 JSON configuration validation."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from netropy_lab.models import LabConfig, lab_config_from_dict
from netropy_lab.validator import (
    ConfigError,
    format_normalized_summary,
    validate_config,
    validate_config_model,
)

CLI_ROOT = Path(__file__).resolve().parents[1]
PROJECT_ROOT = CLI_ROOT.parent
SCHEMA_PATH = PROJECT_ROOT / "config" / "lab-config.schema.json"
INVALID_DIR = PROJECT_ROOT / "config" / "invalid"


def _valid_payload(ssh_key: Path) -> dict:
    return {
        "platform": "kvm",
        "ubuntu_lts_version": "24.04",
        "naming_prefix": "netropy-lab",
        "ssh_public_key_file": str(ssh_key),
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
        "options": {
            "passthrough_data_ports": False,
            "vcpu": 2,
            "memory_mb": 2048,
            "provision_netropy": False,
        },
        "credentials": {"note": "test"},
    }


@pytest.fixture
def ssh_key(tmp_path: Path) -> Path:
    key = tmp_path / "id_ed25519.pub"
    key.write_text("ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAItestkey test@host\n", encoding="utf-8")
    return key


@pytest.fixture
def valid_config_file(tmp_path: Path, ssh_key: Path) -> Path:
    path = tmp_path / "valid.json"
    path.write_text(json.dumps(_valid_payload(ssh_key), indent=2), encoding="utf-8")
    return path


def test_valid_config_returns_normalized_dict(valid_config_file: Path) -> None:
    result = validate_config(valid_config_file, schema_path=SCHEMA_PATH)
    assert result["platform"] == "kvm"
    assert result["naming_prefix"] == "netropy-lab"
    assert result["options"]["provision_netropy"] is False
    assert result["options"]["vcpu"] == 2
    assert "subnets" in result


def test_valid_config_returns_typed_model(valid_config_file: Path) -> None:
    model = validate_config_model(valid_config_file, schema_path=SCHEMA_PATH)
    assert isinstance(model, LabConfig)
    assert model.platform == "kvm"
    assert model.instances.linux1.mgmt_ip == "192.168.100.21"


def test_normalized_summary_contains_defaults(valid_config_file: Path) -> None:
    config = validate_config(valid_config_file, schema_path=SCHEMA_PATH)
    summary = format_normalized_summary(config)
    assert "Normalized lab configuration" in summary
    assert "platform:            kvm" in summary
    assert "192.168.100.0/24" in summary


def test_missing_platform_schema_error(tmp_path: Path, ssh_key: Path) -> None:
    payload = _valid_payload(ssh_key)
    del payload["platform"]
    path = tmp_path / "missing-platform.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ConfigError, match="Schema validation failed"):
        validate_config(path, schema_path=SCHEMA_PATH)


def test_bad_cidr_schema_or_semantic(tmp_path: Path, ssh_key: Path) -> None:
    payload = _valid_payload(ssh_key)
    payload["subnets"]["data1"]["cidr"] = "not-a-cidr"
    path = tmp_path / "bad-cidr.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ConfigError):
        validate_config(path, schema_path=SCHEMA_PATH)


def test_ip_outside_subnet(tmp_path: Path, ssh_key: Path) -> None:
    payload = _valid_payload(ssh_key)
    payload["instances"]["linux1"]["mgmt_ip"] = "10.9.9.21"
    path = tmp_path / "ip-out.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ConfigError, match="not inside subnet"):
        validate_config(path, schema_path=SCHEMA_PATH)


def test_duplicate_ips(tmp_path: Path, ssh_key: Path) -> None:
    payload = _valid_payload(ssh_key)
    payload["instances"]["linux2"]["mgmt_ip"] = payload["instances"]["linux1"]["mgmt_ip"]
    path = tmp_path / "dup.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ConfigError, match="Duplicate IP"):
        validate_config(path, schema_path=SCHEMA_PATH)


def test_overlapping_subnets(tmp_path: Path, ssh_key: Path) -> None:
    payload = _valid_payload(ssh_key)
    payload["subnets"]["data1"]["cidr"] = "192.168.100.0/25"
    payload["instances"]["netropy"]["data1_ip"] = "192.168.100.50"
    payload["instances"]["linux1"]["data_ip"] = "192.168.100.60"
    path = tmp_path / "overlap.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ConfigError, match="Overlapping subnets"):
        validate_config(path, schema_path=SCHEMA_PATH)


def test_bad_vcpu(tmp_path: Path, ssh_key: Path) -> None:
    payload = _valid_payload(ssh_key)
    payload["options"]["vcpu"] = 0
    path = tmp_path / "vcpu.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ConfigError):
        validate_config(path, schema_path=SCHEMA_PATH)


def test_bad_memory(tmp_path: Path, ssh_key: Path) -> None:
    payload = _valid_payload(ssh_key)
    payload["options"]["memory_mb"] = 128
    path = tmp_path / "mem.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ConfigError, match="memory_mb"):
        validate_config(path, schema_path=SCHEMA_PATH)


def test_missing_ssh_key_file(tmp_path: Path) -> None:
    payload = _valid_payload(tmp_path / "does-not-exist.pub")
    path = tmp_path / "nossh.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ConfigError, match="ssh_public_key_file does not exist"):
        validate_config(path, schema_path=SCHEMA_PATH)


def test_netropy_image_required_when_provisioning(tmp_path: Path, ssh_key: Path) -> None:
    payload = _valid_payload(ssh_key)
    payload["options"]["provision_netropy"] = True
    payload.pop("netropy_image", None)
    path = tmp_path / "need-image.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ConfigError, match="netropy_image is required"):
        validate_config(path, schema_path=SCHEMA_PATH)


def test_lab_config_from_dict_applies_defaults(ssh_key: Path) -> None:
    payload = _valid_payload(ssh_key)
    del payload["naming_prefix"]
    del payload["options"]
    model = lab_config_from_dict(payload)
    assert model.naming_prefix == "netropy-lab"
    assert model.options.vcpu == 2
    assert model.options.provision_netropy is True


def test_invalid_sample_files_fail(ssh_key: Path, tmp_path: Path) -> None:
    """Each checked-in invalid sample must fail validation (with a real SSH key path)."""
    samples = [
        "missing-platform.json",
        "bad-cidr.json",
        "ip-outside-subnet.json",
        "duplicate-ips.json",
        "overlapping-subnets.json",
        "bad-vcpu.json",
    ]
    for name in samples:
        raw = json.loads((INVALID_DIR / name).read_text(encoding="utf-8"))
        raw["ssh_public_key_file"] = str(ssh_key)
        path = tmp_path / name
        path.write_text(json.dumps(raw), encoding="utf-8")
        with pytest.raises(ConfigError):
            validate_config(path, schema_path=SCHEMA_PATH)


def test_validate_does_not_import_subprocess_for_tofu() -> None:
    """Smoke check: validator module must not call OpenTofu."""
    import netropy_lab.validator as validator_mod

    source = Path(validator_mod.__file__).read_text(encoding="utf-8")
    assert "tofu" not in source
    assert "subprocess" not in source


def test_aws_platform_rejected(tmp_path: Path, ssh_key: Path) -> None:
    payload = _valid_payload(ssh_key)
    payload["platform"] = "aws"
    path = tmp_path / "aws.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    with pytest.raises(ConfigError, match="Schema validation failed"):
        validate_config(path, schema_path=SCHEMA_PATH)
