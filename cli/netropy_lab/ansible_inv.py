"""Build Ansible inventory for optional post-up configure playbooks."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def build_inventory_ini(config: dict[str, Any]) -> str:
    """Return INI inventory text for linux1/linux2 endpoint hosts."""
    subnets = config["subnets"]
    instances = config["instances"]
    linux1 = instances["linux1"]
    linux2 = instances["linux2"]

    private_key = ""
    pub = config.get("ssh_public_key_file")
    if pub:
        candidate = Path(str(pub)).expanduser()
        if candidate.name.endswith(".pub"):
            candidate = candidate.with_suffix("")
        if candidate.is_file():
            private_key = str(candidate)

    # Linux-1 is on data1; peer subnet is data2. Linux-2 is on data2; peer is data1.
    lines = [
        "[linux_endpoints]",
        (
            f"linux1 ansible_host={linux1['mgmt_ip']} ansible_user=ubuntu "
            f"mgmt_ip={linux1['mgmt_ip']} data_ip={linux1['data_ip']} "
            f"peer_data_cidr={subnets['data2']['cidr']} "
            f"peer_data_ip={linux2['data_ip']}"
        ),
        (
            f"linux2 ansible_host={linux2['mgmt_ip']} ansible_user=ubuntu "
            f"mgmt_ip={linux2['mgmt_ip']} data_ip={linux2['data_ip']} "
            f"peer_data_cidr={subnets['data1']['cidr']} "
            f"peer_data_ip={linux1['data_ip']}"
        ),
        "",
        "[linux_endpoints:vars]",
        "ansible_python_interpreter=auto_silent",
    ]
    if private_key:
        lines.append(f"ansible_ssh_private_key_file={private_key}")
    lines.append("")
    return "\n".join(lines)


def write_inventory(config: dict[str, Any], dest: Path) -> Path:
    """Write generated inventory file and return its path."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(build_inventory_ini(config), encoding="utf-8")
    return dest
