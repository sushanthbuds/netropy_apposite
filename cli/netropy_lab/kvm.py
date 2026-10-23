"""KVM/libvirt helpers for Phase 6 CLI provisioning."""

from __future__ import annotations

import grp
import os
import pwd
import subprocess
import sys
from pathlib import Path
from typing import Literal

from netropy_lab.validator import ConfigError

POOL_PATH = Path("/var/lib/netropy-lab-pool")
VIRSH_URI = "qemu:///system"
TofuAction = Literal["apply", "destroy", "plan"]


def ensure_not_root() -> None:
    if os.geteuid() == 0:
        raise ConfigError(
            "Do not run netropy-lab as root or with sudo. "
            "It uses sg libvirt internally."
        )


def user_in_libvirt_group() -> bool:
    """True if the user is listed in the libvirt group (even if the shell is stale)."""
    try:
        libvirt = grp.getgrnam("libvirt")
    except KeyError:
        return False

    if libvirt.gr_gid in os.getgroups():
        return True

    username = pwd.getpwuid(os.getuid()).pw_name
    return username in libvirt.gr_mem


def can_access_libvirt() -> bool:
    """True if virsh works directly or via sg libvirt (stale group sessions)."""
    probes = (
        ["virsh", "-c", VIRSH_URI, "version"],
        ["sg", "libvirt", "-c", f"virsh -c {VIRSH_URI} version"],
    )
    for cmd in probes:
        result = subprocess.run(cmd, capture_output=True, check=False)
        if result.returncode == 0:
            return True
    return False


def ensure_libvirt_group() -> None:
    try:
        grp.getgrnam("libvirt")
    except KeyError as exc:
        raise ConfigError("libvirt group not found on this host.") from exc

    if can_access_libvirt():
        return

    if not user_in_libvirt_group():
        raise ConfigError(
            "Add your user to the libvirt group, then log in again:\n"
            "  sudo usermod -aG libvirt,kvm $USER"
        )

    raise ConfigError(
        "libvirt is not reachable in this shell. Log out/in, or run:\n"
        "  newgrp libvirt"
    )


def run_virsh(
    *args: str,
    timeout: int | None = None,
) -> subprocess.CompletedProcess[str]:
    """Run virsh on qemu:///system; fall back to sg libvirt when needed."""
    base = ["virsh", "-c", VIRSH_URI, *args]
    direct = subprocess.run(
        base,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )
    if direct.returncode == 0:
        return direct

    joined = " ".join(base)
    return subprocess.run(
        ["sg", "libvirt", "-c", joined],
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def run_tofu(module_dir: Path, action: TofuAction) -> int:
    """Run OpenTofu under sg libvirt (init -upgrade, then apply/destroy/plan)."""
    ensure_not_root()
    ensure_libvirt_group()

    tofu_cmd = f"tofu init -upgrade && tofu {action}"
    if action in ("apply", "destroy"):
        tofu_cmd += " -auto-approve"

    result = subprocess.run(
        ["sg", "libvirt", "-c", tofu_cmd],
        cwd=module_dir,
        check=False,
    )
    return result.returncode


def ensure_pool() -> None:
    POOL_PATH.mkdir(parents=True, exist_ok=True)


def fix_pool_permissions(project_root: Path) -> None:
    """Best-effort pool and home path fixes (may prompt for sudo password)."""
    home = Path.home()
    print("\nFixing libvirt pool permissions (enter password if prompted)...")
    subprocess.run(
        ["sudo", "chown", "-R", "libvirt-qemu:libvirt", str(POOL_PATH)],
        check=False,
        stderr=subprocess.DEVNULL,
    )
    subprocess.run(["sudo", "chmod", "755", str(POOL_PATH)], check=False)
    for entry in POOL_PATH.iterdir():
        subprocess.run(["sudo", "chmod", "660", str(entry)], check=False)
    subprocess.run(["sudo", "chmod", "o+x", str(home), str(project_root)], check=False)


def lab_vm_names(naming_prefix: str, *, provision_netropy: bool) -> list[str]:
    names = [f"{naming_prefix}-linux1", f"{naming_prefix}-linux2"]
    if provision_netropy:
        names.append(f"{naming_prefix}-netropy")
    return names


def ensure_vms_running(vm_names: list[str]) -> None:
    print("\nEnsuring VMs autostart and are running...")
    for vm in vm_names:
        info = subprocess.run(
            ["virsh", "-c", VIRSH_URI, "dominfo", vm],
            check=False,
            capture_output=True,
        )
        if info.returncode != 0:
            print(f"  {vm}: not found (apply may have failed)", file=sys.stderr)
            continue

        subprocess.run(
            ["virsh", "-c", VIRSH_URI, "autostart", vm],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        state = subprocess.run(
            ["virsh", "-c", VIRSH_URI, "domstate", vm],
            check=False,
            capture_output=True,
            text=True,
        )
        current = (state.stdout or "").strip()
        if current == "running":
            print(f"  {vm}: already running")
            continue

        start = subprocess.run(["virsh", "-c", VIRSH_URI, "start", vm], check=False)
        if start.returncode == 0:
            subprocess.run(
                ["virsh", "-c", VIRSH_URI, "qemu-monitor-command", vm, "--hmp", "cont"],
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            print(f"  {vm}: started")
        else:
            print(f"  {vm}: failed to start", file=sys.stderr)


def confirm_destroy(*, force: bool) -> None:
    if force or os.environ.get("NETROPY_LAB_CONFIRM_DESTROY") == "yes":
        return

    print(
        "WARNING: This destroys the full KVM lab (VMs, networks, and related state).",
        file=sys.stderr,
    )
    print("See docs/phase_2/security-guardrails.md", file=sys.stderr)
    answer = input("Type 'destroy' to confirm: ")
    if answer != "destroy":
        raise ConfigError("Destroy aborted.")
