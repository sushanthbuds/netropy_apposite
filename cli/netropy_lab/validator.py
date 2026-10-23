"""Validate the JSON lab configuration file.

Layers (Phase 4):
1. JSON syntax
2. JSON Schema structure (config/lab-config.schema.json)
3. Semantic rules (IP membership, duplicates, overlap, paths, sizing)

This module never provisions infrastructure.
"""

from __future__ import annotations

import ipaddress
import json
from pathlib import Path
from typing import Any

from netropy_lab.models import LabConfig, lab_config_from_dict

try:
    import jsonschema
    from jsonschema import Draft202012Validator
except ImportError:  # pragma: no cover - exercised when dep missing
    jsonschema = None  # type: ignore[assignment]
    Draft202012Validator = None  # type: ignore[misc, assignment]


SUPPORTED_PLATFORMS = {"kvm", "esxi"}
REQUIRED_SUBNETS = ("mgmt", "data1", "data2")
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SCHEMA_PATH = PROJECT_ROOT / "config" / "lab-config.schema.json"

VCPU_MIN, VCPU_MAX = 1, 64
MEMORY_MB_MIN, MEMORY_MB_MAX = 512, 131072


class ConfigError(Exception):
    """Raised when the configuration file is invalid."""


def _load_json(path: Path) -> dict[str, Any]:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid JSON in {path}: {exc}") from exc
    except OSError as exc:
        raise ConfigError(f"Cannot read config file {path}: {exc}") from exc
    if not isinstance(data, dict):
        raise ConfigError(f"Config root must be a JSON object (got {type(data).__name__})")
    return data


def _load_schema(schema_path: Path) -> dict[str, Any]:
    try:
        with schema_path.open(encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise ConfigError(f"Cannot load JSON Schema from {schema_path}: {exc}") from exc


def _format_schema_error(error: Any) -> str:
    path = ".".join(str(p) for p in error.absolute_path)
    location = path if path else "(root)"
    return f"Schema validation failed at {location}: {error.message}"


def _validate_schema(config: dict[str, Any], schema_path: Path) -> None:
    if jsonschema is None or Draft202012Validator is None:
        raise ConfigError(
            "jsonschema package is required for structure validation. "
            "Install with: pip install 'jsonschema>=4.0'"
        )
    schema = _load_schema(schema_path)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(config), key=lambda e: list(e.absolute_path))
    if errors:
        raise ConfigError(_format_schema_error(errors[0]))


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


def _check_no_duplicate_ips(instances: dict[str, Any]) -> None:
    labeled: list[tuple[str, str]] = [
        ("instances.netropy.mgmt_ip", instances["netropy"]["mgmt_ip"]),
        ("instances.netropy.data1_ip", instances["netropy"]["data1_ip"]),
        ("instances.netropy.data2_ip", instances["netropy"]["data2_ip"]),
        ("instances.linux1.mgmt_ip", instances["linux1"]["mgmt_ip"]),
        ("instances.linux1.data_ip", instances["linux1"]["data_ip"]),
        ("instances.linux2.mgmt_ip", instances["linux2"]["mgmt_ip"]),
        ("instances.linux2.data_ip", instances["linux2"]["data_ip"]),
    ]
    seen: dict[str, str] = {}
    for label, ip in labeled:
        if ip in seen:
            raise ConfigError(
                f"Duplicate IP {ip}: used by both {seen[ip]} and {label}"
            )
        seen[ip] = label


def _check_no_subnet_overlap(networks: dict[str, ipaddress.IPv4Network]) -> None:
    names = list(networks.keys())
    for i, left_name in enumerate(names):
        for right_name in names[i + 1 :]:
            left = networks[left_name]
            right = networks[right_name]
            if left.overlaps(right):
                raise ConfigError(
                    f"Overlapping subnets: subnets.{left_name} ({left}) "
                    f"overlaps subnets.{right_name} ({right})"
                )


def _check_options_sizing(options: dict[str, Any]) -> None:
    if "vcpu" in options:
        vcpu = options["vcpu"]
        if not isinstance(vcpu, int) or isinstance(vcpu, bool):
            raise ConfigError("options.vcpu must be an integer")
        if vcpu < VCPU_MIN or vcpu > VCPU_MAX:
            raise ConfigError(
                f"options.vcpu must be between {VCPU_MIN} and {VCPU_MAX} (got {vcpu})"
            )
    if "memory_mb" in options:
        memory_mb = options["memory_mb"]
        if not isinstance(memory_mb, int) or isinstance(memory_mb, bool):
            raise ConfigError("options.memory_mb must be an integer")
        if memory_mb < MEMORY_MB_MIN or memory_mb > MEMORY_MB_MAX:
            raise ConfigError(
                f"options.memory_mb must be between {MEMORY_MB_MIN} and "
                f"{MEMORY_MB_MAX} (got {memory_mb})"
            )


def _validate_semantics(config: dict[str, Any]) -> None:
    platform = config["platform"]
    if platform not in SUPPORTED_PLATFORMS:
        raise ConfigError(
            f"platform must be one of {sorted(SUPPORTED_PLATFORMS)} (got {platform!r})"
        )

    ssh_key_file = config["ssh_public_key_file"]
    expanded_key = Path(ssh_key_file).expanduser()
    if not expanded_key.exists():
        raise ConfigError(f"ssh_public_key_file does not exist: {expanded_key}")
    if not expanded_key.is_file():
        raise ConfigError(f"ssh_public_key_file is not a file: {expanded_key}")

    subnets = config["subnets"]
    parsed_subnets: dict[str, ipaddress.IPv4Network] = {}
    for name in REQUIRED_SUBNETS:
        parsed_subnets[name] = _parse_cidr(
            subnets[name]["cidr"], f"subnets.{name}.cidr"
        )
    _check_no_subnet_overlap(parsed_subnets)

    instances = config["instances"]
    netropy = instances["netropy"]
    for field, subnet_name in (
        ("mgmt_ip", "mgmt"),
        ("data1_ip", "data1"),
        ("data2_ip", "data2"),
    ):
        _ip_in_subnet(
            netropy[field], parsed_subnets[subnet_name], f"instances.netropy.{field}"
        )

    linux1 = instances["linux1"]
    for field, subnet_name in (("mgmt_ip", "mgmt"), ("data_ip", "data1")):
        _ip_in_subnet(
            linux1[field], parsed_subnets[subnet_name], f"instances.linux1.{field}"
        )

    linux2 = instances["linux2"]
    for field, subnet_name in (("mgmt_ip", "mgmt"), ("data_ip", "data2")):
        _ip_in_subnet(
            linux2[field], parsed_subnets[subnet_name], f"instances.linux2.{field}"
        )

    _check_no_duplicate_ips(instances)

    options = config.get("options") or {}
    if not isinstance(options, dict):
        raise ConfigError("options must be an object")
    _check_options_sizing(options)

    provision_netropy = options.get("provision_netropy", True)
    if provision_netropy:
        image_path = config.get("netropy_image")
        if not image_path:
            raise ConfigError(
                "netropy_image is required when options.provision_netropy is true"
            )
        expanded_image = Path(str(image_path)).expanduser()
        if platform == "kvm" and not expanded_image.exists():
            raise ConfigError(
                f"netropy_image does not exist: {expanded_image} "
                "(set options.provision_netropy to false to skip until image is available)"
            )


def format_normalized_summary(config: LabConfig | dict[str, Any]) -> str:
    """Human-readable normalized summary for a valid config (no secrets)."""
    data = config.to_dict() if isinstance(config, LabConfig) else config
    options = data.get("options") or {}
    lines = [
        "=== Normalized lab configuration ===",
        f"platform:            {data['platform']}",
        f"naming_prefix:       {data.get('naming_prefix', 'netropy-lab')}",
        f"ubuntu_lts_version:  {data['ubuntu_lts_version']}",
        f"ssh_public_key_file: {data['ssh_public_key_file']}",
        f"netropy_image:       {data.get('netropy_image') or '(none)'}",
    ]
    lines.extend(
        [
            "",
            "subnets:",
            f"  mgmt:  {data['subnets']['mgmt']['cidr']}",
            f"  data1: {data['subnets']['data1']['cidr']}",
            f"  data2: {data['subnets']['data2']['cidr']}",
            "",
            "instances:",
            f"  netropy: {data['instances']['netropy']['mgmt_ip']} / "
            f"{data['instances']['netropy']['data1_ip']} / "
            f"{data['instances']['netropy']['data2_ip']}",
            f"  linux1:  {data['instances']['linux1']['mgmt_ip']} / "
            f"{data['instances']['linux1']['data_ip']}",
            f"  linux2:  {data['instances']['linux2']['mgmt_ip']} / "
            f"{data['instances']['linux2']['data_ip']}",
            "",
            "options:",
            f"  provision_netropy:      {options.get('provision_netropy', True)}",
            f"  passthrough_data_ports: {options.get('passthrough_data_ports', False)}",
            f"  vcpu:                   {options.get('vcpu', 2)}",
            f"  memory_mb:              {options.get('memory_mb', 2048)}",
        ]
    )
    return "\n".join(lines)


def validate_config(
    path: Path,
    *,
    schema_path: Path | None = None,
) -> dict[str, Any]:
    """Load and validate a lab configuration file.

    Returns a normalized dict (defaults applied). Never provisions resources.
    """
    if not path.exists():
        raise ConfigError(f"Config file not found: {path}")

    raw = _load_json(path)
    _validate_schema(raw, schema_path or DEFAULT_SCHEMA_PATH)
    _validate_semantics(raw)

    lab = lab_config_from_dict(raw)
    return lab.to_dict()


def validate_config_model(
    path: Path,
    *,
    schema_path: Path | None = None,
) -> LabConfig:
    """Validate and return a typed LabConfig model."""
    data = validate_config(path, schema_path=schema_path)
    return lab_config_from_dict(data)
