"""Validate the JSON lab configuration file."""

from __future__ import annotations

import ipaddress
import json
from pathlib import Path
from typing import Any


SUPPORTED_PLATFORMS = {"kvm", "esxi", "aws"}
REQUIRED_SUBNETS = ("mgmt", "data1", "data2")


class ConfigError(Exception):
    """Raised when the configuration file is invalid."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc}") from exc


def _require_mapping(data: dict[str, Any], key: str) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        raise ConfigError(f"Missing or invalid '{key}' object")
    return value


def _parse_cidr(cidr: str, label: str) -> ipaddress.IPv4Network:
    try:
        network = ipaddress.ip_network(cidr, strict=False)
    except ValueError as exc:
        raise ConfigError(f"Invalid CIDR for {label}: {cidr}") from exc
    if network.version != 4:
        raise ConfigError(f"{label} must be an IPv4 subnet (got {cidr})")
    return network


def _parse_ip(ip: str, label: str) -> ipaddress.IPv4Address:
    try:
        address = ipaddress.ip_address(ip)
    except ValueError as exc:
        raise ConfigError(f"Invalid IP for {label}: {ip}") from exc
    if address.version != 4:
        raise ConfigError(f"{label} must be an IPv4 address (got {ip})")
    return address


def _ip_in_subnet(ip: str, network: ipaddress.IPv4Network, label: str) -> None:
    address = _parse_ip(ip, label)
    if address not in network:
        raise ConfigError(f"{label} ({ip}) is not inside subnet {network}")


def validate_config(path: Path) -> dict[str, Any]:
    """Load and validate a lab configuration file."""
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    config = _load_json(path)

    platform = config.get("platform")
    if platform not in SUPPORTED_PLATFORMS:
        raise ConfigError(
            f"platform must be one of {sorted(SUPPORTED_PLATFORMS)} (got {platform!r})"
        )

    if not config.get("ubuntu_lts_version"):
        raise ConfigError("ubuntu_lts_version is required")

    ssh_key_file = config.get("ssh_public_key_file")
    if not ssh_key_file:
        raise ConfigError("ssh_public_key_file is required")
    expanded_key = Path(ssh_key_file).expanduser()
    if not expanded_key.exists():
        raise ConfigError(f"ssh_public_key_file does not exist: {expanded_key}")

    subnets = _require_mapping(config, "subnets")
    parsed_subnets: dict[str, ipaddress.IPv4Network] = {}
    for name in REQUIRED_SUBNETS:
        entry = subnets.get(name)
        if not isinstance(entry, dict) or not entry.get("cidr"):
            raise ConfigError(f"subnets.{name}.cidr is required")
        parsed_subnets[name] = _parse_cidr(entry["cidr"], f"subnets.{name}")

    instances = _require_mapping(config, "instances")
    for role in ("netropy", "linux1", "linux2"):
        if role not in instances:
            raise ConfigError(f"instances.{role} is required")

    netropy = instances["netropy"]
    for field, subnet_name in (
        ("mgmt_ip", "mgmt"),
        ("data1_ip", "data1"),
        ("data2_ip", "data2"),
    ):
        if field not in netropy:
            raise ConfigError(f"instances.netropy.{field} is required")
        _ip_in_subnet(netropy[field], parsed_subnets[subnet_name], f"netropy.{field}")

    linux1 = instances["linux1"]
    for field, subnet_name in (("mgmt_ip", "mgmt"), ("data_ip", "data1")):
        if field not in linux1:
            raise ConfigError(f"instances.linux1.{field} is required")
        _ip_in_subnet(linux1[field], parsed_subnets[subnet_name], f"linux1.{field}")

    linux2 = instances["linux2"]
    for field, subnet_name in (("mgmt_ip", "mgmt"), ("data_ip", "data2")):
        if field not in linux2:
            raise ConfigError(f"instances.linux2.{field} is required")
        _ip_in_subnet(linux2[field], parsed_subnets[subnet_name], f"linux2.{field}")

    options = config.get("options", {})
    provision_netropy = options.get("provision_netropy", True)
    if provision_netropy:
        image_path = config.get("netropy_image")
        if not image_path:
            raise ConfigError("netropy_image is required when provision_netropy is true")
        if platform == "kvm" and not Path(image_path).expanduser().exists():
            raise ConfigError(
                f"netropy_image does not exist: {image_path} "
                "(set options.provision_netropy to false to skip until image is available)"
            )

    return config
