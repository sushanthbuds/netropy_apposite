"""Build OpenTofu auto.tfvars payloads for platform modules.

Single source of truth shared by the CLI and modules/*/run helpers.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from netropy_lab.validator import ConfigError

DEFAULT_UBUNTU_IMAGE = Path("/var/lib/netropy-lab-images/noble-server-cloudimg-amd64.img")
DEFAULT_NETROPY_CONFIG_DISK_NAME = "vn-disk2-256m-5.1.3.qcow2"


def resolve_netropy_config_image(config: dict[str, Any]) -> str:
    """Return the Netropy /config disk path (explicit JSON or sibling of disk1)."""
    explicit = config.get("netropy_config_image") or ""
    if explicit:
        return str(Path(explicit).expanduser())

    netropy_image = config.get("netropy_image") or ""
    if not netropy_image:
        return ""

    sibling = Path(netropy_image).expanduser().resolve().parent / DEFAULT_NETROPY_CONFIG_DISK_NAME
    if sibling.is_file():
        return str(sibling)
    return ""


def build_kvm_tfvars_payload(config: dict[str, Any]) -> dict[str, Any]:
    """Build the variable payload passed to the OpenTofu KVM module."""
    netropy_image = config.get("netropy_image", "")
    config_image = resolve_netropy_config_image(config)
    provision_netropy = config.get("options", {}).get("provision_netropy", True)

    if provision_netropy and not config_image:
        raise ConfigError(
            "netropy_config_image missing: convert OVA disk2 to "
            f"Netropy-VM/{DEFAULT_NETROPY_CONFIG_DISK_NAME} "
            "or set netropy_config_image in the JSON config"
        )

    return {
        "naming_prefix": config.get("naming_prefix", "netropy-lab"),
        "ssh_public_key": Path(config["ssh_public_key_file"]).expanduser().read_text().strip(),
        "subnets": config["subnets"],
        "instances": config["instances"],
        "options": config.get("options", {}),
        "netropy_image": netropy_image,
        "netropy_config_image": config_image,
        "ubuntu_image": str(DEFAULT_UBUNTU_IMAGE),
    }


def build_tfvars_payload(config: dict[str, Any]) -> dict[str, Any]:
    """Build tfvars for the config platform (kvm)."""
    platform = config.get("platform", "kvm")
    if platform == "kvm":
        return build_kvm_tfvars_payload(config)
    raise ConfigError(
        f"tfvars generation is not implemented for platform {platform!r} yet"
    )


def write_tfvars(config: dict[str, Any], dest: Path) -> None:
    """Write lab.auto.tfvars.json for OpenTofu."""
    payload = build_tfvars_payload(config)
    dest.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
