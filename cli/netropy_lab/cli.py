"""Command-line interface for the Netropy lab provisioner."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

from netropy_lab.validator import ConfigError, validate_config

PROJECT_ROOT = Path(__file__).resolve().parents[2]
MODULE_DIRS = {
    "kvm": PROJECT_ROOT / "modules" / "kvm",
    "esxi": PROJECT_ROOT / "modules" / "esxi",
    "aws": PROJECT_ROOT / "modules" / "aws",
}


def _tfvars_payload(config: dict) -> dict:
    """Build the variable payload passed to the OpenTofu module."""
    return {
        "naming_prefix": config.get("naming_prefix", "netropy-lab"),
        "ssh_public_key": Path(config["ssh_public_key_file"]).expanduser().read_text().strip(),
        "subnets": config["subnets"],
        "instances": config["instances"],
        "options": config.get("options", {}),
        "netropy_image": config.get("netropy_image", ""),
        "ubuntu_image": str(PROJECT_ROOT / "images" / "noble-server-cloudimg-amd64.img"),
    }


def _write_tfvars(config: dict, dest: Path) -> None:
    dest.write_text(json.dumps(_tfvars_payload(config), indent=2) + "\n", encoding="utf-8")


def _run_tofu(module_dir: Path, command: str) -> int:
    tofu = "tofu"
    init = subprocess.run([tofu, "init"], cwd=module_dir, check=False)
    if init.returncode != 0:
        return init.returncode

    cmd = [tofu, command, "-auto-approve"]
    result = subprocess.run(cmd, cwd=module_dir, check=False)
    return result.returncode


def _print_summary(config: dict) -> None:
    instances = config["instances"]
    prefix = config.get("naming_prefix", "netropy-lab")
    print("\n=== Netropy Lab Access Summary ===\n")
    print(f"Lab prefix: {prefix}\n")

    print("Linux-1 (traffic endpoint A)")
    print(f"  Mgmt IP:  {instances['linux1']['mgmt_ip']}")
    print(f"  Data IP:  {instances['linux1']['data_ip']}")
    print(f"  SSH:      ssh ubuntu@{instances['linux1']['mgmt_ip']}\n")

    print("Linux-2 (traffic endpoint B)")
    print(f"  Mgmt IP:  {instances['linux2']['mgmt_ip']}")
    print(f"  Data IP:  {instances['linux2']['data_ip']}")
    print(f"  SSH:      ssh ubuntu@{instances['linux2']['mgmt_ip']}\n")

    if config.get("options", {}).get("provision_netropy", True):
        netropy = instances["netropy"]
        print("Netropy VE")
        print(f"  Mgmt IP:  {netropy['mgmt_ip']}")
        print(f"  Data1 IP: {netropy['data1_ip']}")
        print(f"  Data2 IP: {netropy['data2_ip']}")
        print(f"  Web UI:   https://{netropy['mgmt_ip']}/ (confirm with team)\n")
    else:
        print("Netropy VE: skipped (provision_netropy=false)\n")

    print("End-to-end iperf3 test (after configuring Netropy):")
    print(
        f"  iperf3 -c {instances['linux2']['data_ip']} "
        f"-B {instances['linux1']['data_ip']}"
    )
    print()


def cmd_validate(args: argparse.Namespace) -> int:
    config_path = Path(args.config).expanduser()
    try:
        validate_config(config_path)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1
    print(f"Config OK: {config_path}")
    return 0


def cmd_up(args: argparse.Namespace) -> int:
    config_path = Path(args.config).expanduser()
    try:
        config = validate_config(config_path)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    platform = config["platform"]
    module_dir = MODULE_DIRS.get(platform)
    if module_dir is None or not module_dir.exists():
        print(f"Platform module not found: {module_dir}", file=sys.stderr)
        return 1

    tfvars = module_dir / "lab.auto.tfvars.json"
    _write_tfvars(config, tfvars)

    print(f"Provisioning lab on {platform}...")
    rc = _run_tofu(module_dir, "apply")
    if rc == 0:
        _print_summary(config)
    return rc


def cmd_down(args: argparse.Namespace) -> int:
    config_path = Path(args.config).expanduser()
    try:
        config = validate_config(config_path)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    platform = config["platform"]
    module_dir = MODULE_DIRS.get(platform)
    if module_dir is None or not module_dir.exists():
        print(f"Platform module not found: {module_dir}", file=sys.stderr)
        return 1

    tfvars = module_dir / "lab.auto.tfvars.json"
    if not tfvars.exists():
        _write_tfvars(config, tfvars)

    print(f"Destroying lab on {platform}...")
    return _run_tofu(module_dir, "destroy")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="netropy-lab",
        description="Provision a Netropy VE test lab from a JSON config file",
    )
    default_config = str(PROJECT_ROOT / "config" / "example-kvm.json")
    parser.add_argument(
        "-c",
        "--config",
        default=default_config,
        help="Path to the JSON lab configuration file",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    validate_parser = sub.add_parser("validate", help="Validate the JSON config")
    validate_parser.add_argument("-c", "--config", default=default_config)
    validate_parser.set_defaults(func=cmd_validate)

    up_parser = sub.add_parser("up", help="Create or update the lab")
    up_parser.add_argument("-c", "--config", default=default_config)
    up_parser.set_defaults(func=cmd_up)

    down_parser = sub.add_parser("down", help="Destroy the lab")
    down_parser.add_argument("-c", "--config", default=default_config)
    down_parser.set_defaults(func=cmd_down)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
