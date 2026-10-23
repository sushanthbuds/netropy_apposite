#!/usr/bin/env python3
"""Render the ESXi demo-lab guest files from lab-parameters.json.

Writes into output/:
  linux1-netplan.yaml, linux2-netplan.yaml  static IPs + on-link peer data route
  iperf3-lab.service                         optional iperf3 server unit for Linux-2
  netropy-console.txt                        Netropy management IP command

Then prints the names to type in the ESXi Host Client. Standard library only.
"""

from __future__ import annotations

import argparse
import ipaddress
import json
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
RENDERERS = {"NetworkManager", "networkd"}
OVA_NETWORK_MAP = (("VM Network", "mgmt"), ("TestNetwork-1", "data1"), ("TestNetwork-2", "data2"))


class ParamError(Exception):
    """Raised when lab-parameters.json is invalid."""


def _network(params: dict[str, Any], name: str) -> ipaddress.IPv4Network:
    try:
        cidr = params["subnets"][name]["cidr"]
        network = ipaddress.ip_network(cidr, strict=True)
    except KeyError as exc:
        raise ParamError(f"subnets.{name}.cidr is missing") from exc
    except ValueError as exc:
        raise ParamError(f"subnets.{name}.cidr is not a valid network address: {exc}") from exc
    if network.version != 4:
        raise ParamError(f"subnets.{name}.cidr must be IPv4")
    return network


def _host_ip(params: dict[str, Any], vm: str, field: str, network: ipaddress.IPv4Network) -> str:
    label = f"instances.{vm}.{field}"
    try:
        address = ipaddress.ip_address(params["instances"][vm][field])
    except KeyError as exc:
        raise ParamError(f"{label} is missing") from exc
    except ValueError as exc:
        raise ParamError(f"{label} is not a valid IP: {exc}") from exc
    if address not in network or address in (network.network_address, network.broadcast_address):
        raise ParamError(f"{label} ({address}) is not a usable host address in {network}")
    return str(address)


def validate(params: dict[str, Any]) -> dict[str, Any]:
    prefix = params.get("naming_prefix", "")
    if not prefix:
        raise ParamError("naming_prefix must not be empty")

    nets = {name: _network(params, name) for name in ("mgmt", "data1", "data2")}
    names = list(nets)
    for i, left in enumerate(names):
        for right in names[i + 1 :]:
            if nets[left].overlaps(nets[right]):
                raise ParamError(f"subnets.{left} overlaps subnets.{right}")

    ips = {
        "netropy_mgmt": _host_ip(params, "netropy", "mgmt_ip", nets["mgmt"]),
        "linux1_mgmt": _host_ip(params, "linux1", "mgmt_ip", nets["mgmt"]),
        "linux1_data": _host_ip(params, "linux1", "data_ip", nets["data1"]),
        "linux2_mgmt": _host_ip(params, "linux2", "mgmt_ip", nets["mgmt"]),
        "linux2_data": _host_ip(params, "linux2", "data_ip", nets["data2"]),
    }
    if len(set(ips.values())) != len(ips):
        raise ParamError("instances contain a duplicate IP address")

    guest = params.get("linux_guest", {})
    nics = [guest.get("mgmt_nic", ""), guest.get("data_nic", "")]
    if guest.get("internet_nic"):
        nics.append(guest["internet_nic"])
    if not all(nics[:2]) or len(set(nics)) != len(nics):
        raise ParamError("linux_guest NIC names must be set and different from each other")
    if guest.get("netplan_renderer") not in RENDERERS:
        raise ParamError(f"linux_guest.netplan_renderer must be one of {sorted(RENDERERS)}")

    return {"prefix": prefix, "nets": nets, "ips": ips, "guest": guest}


def render_netplan(
    lab: dict[str, Any], mgmt_ip: str, data_ip: str, data_net: str, peer_net: str
) -> str:
    guest, nets, prefix = lab["guest"], lab["nets"], lab["prefix"]
    lines = [
        "network:",
        "  version: 2",
        f"  renderer: {guest['netplan_renderer']}",
        "  ethernets:",
    ]
    for nic, port_group, address, route in (
        (guest["mgmt_nic"], f"{prefix}-mgmt", f"{mgmt_ip}/{nets['mgmt'].prefixlen}", None),
        (guest["data_nic"], f"{prefix}-{data_net}", f"{data_ip}/{nets[data_net].prefixlen}", nets[peer_net]),
    ):
        lines += [
            f"    {nic}:                 # {port_group}",
            "      dhcp4: false",
            "      dhcp6: false",
            "      accept-ra: false",
            f"      addresses: [{address}]",
        ]
        if route is not None:
            lines += ["      routes:", f"        - to: {route}", "          scope: link"]
    if guest.get("internet_nic"):
        lines += [f"    {guest['internet_nic']}:                 # internet (DHCP)", "      dhcp4: true"]
    return "\n".join(lines) + "\n"


def render_iperf3_unit(linux2_data_ip: str) -> str:
    return (
        "[Unit]\n"
        "Description=iperf3 server on the Netropy lab data network\n"
        "After=network-online.target\n"
        "Wants=network-online.target\n"
        "\n"
        "[Service]\n"
        f"ExecStart=/usr/bin/iperf3 -s -B {linux2_data_ip}\n"
        "Restart=always\n"
        "RestartSec=5\n"
        "\n"
        "[Install]\n"
        "WantedBy=multi-user.target\n"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-p", "--params", default=str(HERE / "lab-parameters.json"))
    parser.add_argument("-o", "--output", default=str(HERE / "output"))
    args = parser.parse_args(argv)

    try:
        params = json.loads(Path(args.params).read_text(encoding="utf-8"))
        lab = validate(params)
    except (OSError, json.JSONDecodeError, ParamError) as exc:
        print(f"Parameter error: {exc}", file=sys.stderr)
        return 1

    prefix, nets, ips = lab["prefix"], lab["nets"], lab["ips"]
    esxi = params.get("esxi", {})
    internet_pg = esxi.get("internet_port_group", "VM Network")
    netmask = nets["mgmt"].netmask
    console_cmd = f"mgmt set addr {ips['netropy_mgmt']} netmask {netmask}"

    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=True)
    files = {
        "linux1-netplan.yaml": render_netplan(lab, ips["linux1_mgmt"], ips["linux1_data"], "data1", "data2"),
        "linux2-netplan.yaml": render_netplan(lab, ips["linux2_mgmt"], ips["linux2_data"], "data2", "data1"),
        "iperf3-lab.service": render_iperf3_unit(ips["linux2_data"]),
        "netropy-console.txt": f"{console_cmd}\nmgmt show\n",
    }
    for name, content in files.items():
        (out / name).write_text(content, encoding="utf-8")

    print("=== ESXi Host Client names (from lab-parameters.json) ===\n")
    print(f"Datastore: {esxi.get('datastore', '?')}   Ubuntu ISO: {esxi.get('ubuntu_iso', '?')}\n")
    print("Virtual switches (no uplinks) and port groups:")
    for name in ("mgmt", "data1", "data2"):
        print(f"  vSwitch-{prefix}-{name:<6} -> port group {prefix}-{name}   ({nets[name]})")
    print("\nVMs and network adapters:")
    print(f"  {prefix}-linux1   1={prefix}-mgmt  2={prefix}-data1  3={internet_pg}")
    print(f"  {prefix}-linux2   1={prefix}-mgmt  2={prefix}-data2  3={internet_pg}")
    ova_map = ", ".join(f"{src} -> {prefix}-{dst}" for src, dst in OVA_NETWORK_MAP)
    print(f"  {prefix}-netropy  OVA {esxi.get('netropy_ova', '?')}: {ova_map}")
    print(f"\nNetropy console: {console_cmd}")
    print(f"Netropy web UI:  http://{ips['netropy_mgmt']} (via SSH tunnel)")
    print("\nTraffic test:")
    print(f"  Linux-2: iperf3 -s -B {ips['linux2_data']}")
    print(f"  Linux-1: iperf3 -c {ips['linux2_data']} -B {ips['linux1_data']}")
    print(f"\nWrote {len(files)} files to {out}/:")
    for name in files:
        print(f"  {name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
