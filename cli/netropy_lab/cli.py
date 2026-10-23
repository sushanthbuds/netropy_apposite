"""Command-line interface for the Netropy lab provisioner."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

from netropy_lab import kvm
from netropy_lab.ansible_inv import write_inventory
from netropy_lab.tfvars import write_tfvars
from netropy_lab.validator import ConfigError, format_normalized_summary, validate_config
from netropy_lab.verify import (
    exit_code_for_results,
    format_verify_report,
    verify_kvm_lab,
    write_failure_bundle,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ANSIBLE_DIR = PROJECT_ROOT / "ansible"
ANSIBLE_PLAYBOOK = ANSIBLE_DIR / "playbooks" / "configure-routes.yml"
ANSIBLE_INVENTORY = ANSIBLE_DIR / "inventory" / "lab.generated.ini"
MODULE_DIRS = {
    "kvm": PROJECT_ROOT / "modules" / "kvm",
    "esxi": PROJECT_ROOT / "modules" / "esxi",
}


def _resolve_module(config: dict) -> tuple[str, Path]:
    platform = config["platform"]
    module_dir = MODULE_DIRS.get(platform)
    if module_dir is None or not module_dir.exists():
        raise ConfigError(f"Platform module not found: {module_dir}")
    return platform, module_dir


def _prepare_tfvars(config: dict, module_dir: Path) -> Path:
    tfvars = module_dir / "lab.auto.tfvars.json"
    write_tfvars(config, tfvars)
    return tfvars


def _kvm_preflight(*, ensure_pool_dir: bool = False) -> None:
    kvm.ensure_not_root()
    kvm.ensure_libvirt_group()
    if ensure_pool_dir:
        kvm.ensure_pool()


def _run_platform_tofu(platform: str, module_dir: Path, action: kvm.TofuAction) -> int:
    if platform == "kvm":
        return kvm.run_tofu(module_dir, action)
    raise ConfigError(f"OpenTofu provisioning for platform '{platform}' is not implemented yet.")


def _kvm_post_apply(config: dict) -> None:
    prefix = config.get("naming_prefix", "netropy-lab")
    provision_netropy = config.get("options", {}).get("provision_netropy", True)
    kvm.ensure_pool()
    kvm.fix_pool_permissions(PROJECT_ROOT)
    kvm.ensure_vms_running(kvm.lab_vm_names(prefix, provision_netropy=provision_netropy))


def _print_summary(config: dict) -> None:
    instances = config["instances"]
    prefix = config.get("naming_prefix", "netropy-lab")
    print("\n=== Netropy Lab Access Summary ===\n")
    print(f"Lab prefix: {prefix}\n")

    linux1_ssh_host = instances["linux1"]["mgmt_ip"]
    linux2_ssh_host = instances["linux2"]["mgmt_ip"]

    print("Linux-1 (traffic endpoint A)")
    print(f"  Mgmt IP:  {instances['linux1']['mgmt_ip']}")
    print(f"  Data IP:  {instances['linux1']['data_ip']}")
    print(f"  SSH:      ssh ubuntu@{linux1_ssh_host}\n")

    print("Linux-2 (traffic endpoint B)")
    print(f"  Mgmt IP:  {instances['linux2']['mgmt_ip']}")
    print(f"  Data IP:  {instances['linux2']['data_ip']}")
    print(f"  SSH:      ssh ubuntu@{linux2_ssh_host}\n")

    if config.get("options", {}).get("provision_netropy", True):
        netropy = instances["netropy"]
        netropy_host = netropy["mgmt_ip"]
        print("Netropy VE")
        print(f"  Mgmt IP:  {netropy['mgmt_ip']}")
        print(f"  Data1 IP: {netropy['data1_ip']}")
        print(f"  Data2 IP: {netropy['data2_ip']}")
        print(f"  SSH:      ssh admin@{netropy_host}")
        print(f"  Web UI:   http://{netropy_host}")
        print("  Auth:     product default user admin (password not stored in git)\n")
    else:
        print("Netropy VE: skipped (provision_netropy=false)\n")

    print("Wait ~90 seconds for cloud-init on the Linux VMs, then:")
    print(f"  ping -c 3 {linux1_ssh_host}")
    print(f"  ping -c 3 {linux2_ssh_host}")
    print("\nEnd-to-end iperf3 test (after configuring Netropy):")
    print(
        f"  iperf3 -c {instances['linux2']['data_ip']} "
        f"-B {instances['linux1']['data_ip']}"
    )
    print()


def cmd_validate(args: argparse.Namespace) -> int:
    """Validate JSON only — never provisions or calls OpenTofu."""
    config_path = Path(args.config).expanduser()
    try:
        config = validate_config(config_path)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1
    print(f"Config OK: {config_path}")
    print()
    print(format_normalized_summary(config))
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    config_path = Path(args.config).expanduser()
    try:
        config = validate_config(config_path)
        platform, module_dir = _resolve_module(config)
        _prepare_tfvars(config, module_dir)
        if platform == "kvm":
            _kvm_preflight()
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    print(f"Planning lab on {platform}...")
    return _run_platform_tofu(platform, module_dir, "plan")


def cmd_verify(args: argparse.Namespace) -> int:
    config_path = Path(args.config).expanduser()
    try:
        config = validate_config(config_path)
        platform = config["platform"]
        if platform == "kvm":
            kvm.ensure_not_root()
            kvm.ensure_libvirt_group()
            results = verify_kvm_lab(config)
        else:
            raise ConfigError(f"verify is not implemented for platform {platform!r}")
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    print(format_verify_report(results, config_path=str(config_path)))

    exit_code = exit_code_for_results(
        results,
        require_forwarding=getattr(args, "require_forwarding", False),
    )
    bundle = getattr(args, "bundle", None)
    if bundle and exit_code != 0:
        write_failure_bundle(
            Path(bundle).expanduser(),
            config_path=config_path,
            results=results,
        )
    return exit_code


def cmd_up(args: argparse.Namespace) -> int:
    config_path = Path(args.config).expanduser()
    try:
        config = validate_config(config_path)
        platform, module_dir = _resolve_module(config)
        _prepare_tfvars(config, module_dir)
        if platform == "kvm":
            _kvm_preflight(ensure_pool_dir=True)
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    print(f"Provisioning lab on {platform}...")
    rc = _run_platform_tofu(platform, module_dir, "apply")
    if rc != 0:
        return rc

    if platform == "kvm":
        _kvm_post_apply(config)

    _print_summary(config)
    return 0


def cmd_down(args: argparse.Namespace) -> int:
    config_path = Path(args.config).expanduser()
    try:
        config = validate_config(config_path)
        platform, module_dir = _resolve_module(config)
        tfvars = module_dir / "lab.auto.tfvars.json"
        if not tfvars.exists():
            _prepare_tfvars(config, module_dir)
        if platform == "kvm":
            _kvm_preflight()
            kvm.confirm_destroy(force=getattr(args, "yes", False))
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    print(f"Destroying lab on {platform}...")
    return _run_platform_tofu(platform, module_dir, "destroy")


def cmd_configure(args: argparse.Namespace) -> int:
    """Run optional Ansible playbook to install on-link data routes."""
    config_path = Path(args.config).expanduser()
    try:
        config = validate_config(config_path)
        platform = config["platform"]
        if platform != "kvm":
            raise ConfigError(
                f"configure is only implemented for kvm (got {platform!r})"
            )
        ansible_playbook = shutil.which("ansible-playbook")
        if not ansible_playbook:
            raise ConfigError(
                "ansible-playbook not found on PATH. Install ansible-core, e.g. "
                "'sudo apt install -y ansible-core' or 'pip install --user ansible-core'"
            )
        if not ANSIBLE_PLAYBOOK.is_file():
            raise ConfigError(f"Ansible playbook not found: {ANSIBLE_PLAYBOOK}")
    except ConfigError as exc:
        print(f"Config error: {exc}", file=sys.stderr)
        return 1

    inventory_path = write_inventory(config, ANSIBLE_INVENTORY)
    print(f"Wrote Ansible inventory: {inventory_path}")
    print("Configuring on-link data routes via Ansible...")
    result = subprocess.run(
        [
            ansible_playbook,
            "-i",
            str(inventory_path),
            str(ANSIBLE_PLAYBOOK),
        ],
        cwd=ANSIBLE_DIR,
        check=False,
    )
    if result.returncode != 0:
        print(
            "Ansible configure failed. Confirm the lab is up, SSH works "
            "(ssh-keygen -R <host> after recreate), and Netropy Bridge "
            "is enabled if peer pings fail.",
            file=sys.stderr,
        )
        return result.returncode

    print("Configure complete. Next:")
    print(
        "  PYTHONPATH=cli python3 -m netropy_lab.cli verify "
        f"-c {config_path} --require-forwarding"
    )
    return 0


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

    plan_parser = sub.add_parser("plan", help="Show OpenTofu plan without applying")
    plan_parser.add_argument("-c", "--config", default=default_config)
    plan_parser.set_defaults(func=cmd_plan)

    up_parser = sub.add_parser("up", help="Create or update the lab")
    up_parser.add_argument("-c", "--config", default=default_config)
    up_parser.set_defaults(func=cmd_up)

    down_parser = sub.add_parser("down", help="Destroy the lab")
    down_parser.add_argument("-c", "--config", default=default_config)
    down_parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip interactive destroy confirmation",
    )
    down_parser.set_defaults(func=cmd_down)
    verify_parser = sub.add_parser("verify", help="Check lab health after up")
    verify_parser.add_argument("-c", "--config", default=default_config)
    verify_parser.add_argument(
        "--require-forwarding",
        action="store_true",
        help="Exit non-zero unless data-path checks pass",
    )
    verify_parser.add_argument(
        "--bundle",
        metavar="PATH",
        help="Write JSON failure report when verify exits non-zero",
    )
    verify_parser.set_defaults(func=cmd_verify)

    configure_parser = sub.add_parser(
        "configure",
        help="Optional Ansible: add on-link data routes after up (kvm)",
    )
    configure_parser.add_argument("-c", "--config", default=default_config)
    configure_parser.set_defaults(func=cmd_configure)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
