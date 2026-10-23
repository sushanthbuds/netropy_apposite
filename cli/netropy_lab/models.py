"""Typed configuration models for the Netropy lab JSON contract."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SubnetConfig:
    cidr: str


@dataclass(frozen=True)
class SubnetsConfig:
    mgmt: SubnetConfig
    data1: SubnetConfig
    data2: SubnetConfig


@dataclass(frozen=True)
class NetropyInstance:
    mgmt_ip: str
    data1_ip: str
    data2_ip: str


@dataclass(frozen=True)
class LinuxInstance:
    mgmt_ip: str
    data_ip: str


@dataclass(frozen=True)
class InstancesConfig:
    netropy: NetropyInstance
    linux1: LinuxInstance
    linux2: LinuxInstance


@dataclass(frozen=True)
class OptionsConfig:
    provision_netropy: bool = True
    passthrough_data_ports: bool = False
    vcpu: int = 2
    memory_mb: int = 2048


@dataclass(frozen=True)
class LabConfig:
    """Normalized lab configuration after successful validation."""

    platform: str
    ubuntu_lts_version: str
    ssh_public_key_file: str
    subnets: SubnetsConfig
    instances: InstancesConfig
    naming_prefix: str = "netropy-lab"
    netropy_image: str = ""
    options: OptionsConfig = field(default_factory=OptionsConfig)
    credentials: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a plain dict suitable for CLI / OpenTofu tfvars rendering."""
        return asdict(self)


def lab_config_from_dict(data: dict[str, Any]) -> LabConfig:
    """Build LabConfig from a raw (already structure-checked) dict."""
    raw_options = data.get("options") or {}
    options = OptionsConfig(
        provision_netropy=bool(raw_options.get("provision_netropy", True)),
        passthrough_data_ports=bool(raw_options.get("passthrough_data_ports", False)),
        vcpu=int(raw_options.get("vcpu", 2)),
        memory_mb=int(raw_options.get("memory_mb", 2048)),
    )
    subnets = data["subnets"]
    instances = data["instances"]
    return LabConfig(
        platform=str(data["platform"]),
        ubuntu_lts_version=str(data["ubuntu_lts_version"]),
        ssh_public_key_file=str(data["ssh_public_key_file"]),
        naming_prefix=str(data.get("naming_prefix") or "netropy-lab"),
        netropy_image=str(data.get("netropy_image") or ""),
        subnets=SubnetsConfig(
            mgmt=SubnetConfig(cidr=str(subnets["mgmt"]["cidr"])),
            data1=SubnetConfig(cidr=str(subnets["data1"]["cidr"])),
            data2=SubnetConfig(cidr=str(subnets["data2"]["cidr"])),
        ),
        instances=InstancesConfig(
            netropy=NetropyInstance(
                mgmt_ip=str(instances["netropy"]["mgmt_ip"]),
                data1_ip=str(instances["netropy"]["data1_ip"]),
                data2_ip=str(instances["netropy"]["data2_ip"]),
            ),
            linux1=LinuxInstance(
                mgmt_ip=str(instances["linux1"]["mgmt_ip"]),
                data_ip=str(instances["linux1"]["data_ip"]),
            ),
            linux2=LinuxInstance(
                mgmt_ip=str(instances["linux2"]["mgmt_ip"]),
                data_ip=str(instances["linux2"]["data_ip"]),
            ),
        ),
        options=options,
        credentials=dict(data.get("credentials") or {}),
    )
