# Setup demo topology for Netropy WAN Emulator in KVM

This package builds a small Netropy VE demo lab on a single Linux KVM host using
**OpenTofu** (Terraform-compatible) and a thin Python CLI. You edit **one file**
(`config/example-kvm.json`), run one command, and get:

| VM | NICs | Role |
|----|------|------|
| Netropy VE | mgmt + data-1 + data-2 | WAN emulator (bridges data-1 ↔ data-2) |
| Linux-1 (Ubuntu 24.04) | mgmt + data-1 | iperf3 client |
| Linux-2 (Ubuntu 24.04) | mgmt + data-2 | iperf3 server |

Three libvirt networks are created: **mgmt**, **data-1**, **data-2**.
Traffic from Linux-1 to Linux-2 on the data networks must pass through Netropy.
Diagram: [`docs/netropy-topology.svg`](docs/netropy-topology.svg).

Default addresses (change them in the config file if they clash with your network):

| Host | mgmt | data |
|------|------|------|
| Netropy VE | `192.168.100.10` | data-1 `192.168.101.10`, data-2 `192.168.102.10` |
| Linux-1 | `192.168.100.21` | `192.168.101.21` |
| Linux-2 | `192.168.100.22` | `192.168.102.22` |

---

## Package contents

| Path | Purpose |
|------|---------|
| `config/example-kvm.json` | **The only file you edit** — images, SSH key, subnets, IPs, sizing |
| `config/lab-config.schema.json` | JSON Schema used by `validate` (do not edit) |
| `cli/netropy_lab/` | Python CLI: `validate`, `plan`, `up`, `configure`, `verify`, `down` |
| `modules/kvm/` | OpenTofu module (libvirt provider) + cloud-init templates + fallback shell scripts |
| `ansible/` | Optional playbook used by `configure` (adds Linux data routes) |
| `scripts/verify-setup.sh` | Host prerequisite checks |
| `scripts/fix-libvirt-permissions.sh` | Repair disk permissions if VMs fail to boot |

The Netropy VE image and the Ubuntu cloud image are **not** included (see step 3).

---

## 1. Host requirements

- Linux host with hardware virtualization (Intel VT-x / AMD-V). Tested on Ubuntu 22.04.
- **RAM:** at least 12 GiB free. Netropy uses 8 GiB and 8 vCPUs (fixed in `modules/kvm/main.tf`);
  each Linux VM uses the `vcpu` / `memory_mb` from the config (default 2 vCPU, 2 GiB).
- **Disk:** about 10 GiB free under `/var/lib`.
- A normal user account with `sudo` rights. **Do not run the lab commands as root or with `sudo`.**

Tested versions: OpenTofu 1.12.4, Python 3.10, libvirt 8.0.0, QEMU 6.2, Netropy VE 5.1.3.

## 2. One-time host setup

```bash
# KVM, libvirt, and helpers
sudo apt update
sudo apt install -y qemu-system-x86 libvirt-daemon-system libvirt-clients cpu-checker \
                    xorriso python3-venv qemu-utils

# Optional: only needed for the 'configure' step (Linux data routes)
sudo apt install -y ansible-core

# Let your user manage libvirt, then LOG OUT and back in
sudo usermod -aG libvirt,kvm "$USER"

# Folders used by the lab (images + libvirt storage pool)
sudo mkdir -p /var/lib/netropy-lab-images /var/lib/netropy-lab-pool
sudo chown "$USER": /var/lib/netropy-lab-images
```

Install **OpenTofu** (>= 1.6) by following <https://opentofu.org/docs/intro/install/>, then check:

```bash
tofu version
kvm-ok
virsh -c qemu:///system list --all
```

Create a Python virtual environment for the CLI dependency (run from this package folder):

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install 'jsonschema>=4.0'
```

Run `source .venv/bin/activate` again in every new terminal before using the commands below.

You also need an SSH key pair. If `~/.ssh/id_ed25519.pub` does not exist:

```bash
ssh-keygen -t ed25519
```

## 3. Get the images

### Ubuntu 24.04 cloud image (fixed location)

```bash
wget -O /var/lib/netropy-lab-images/noble-server-cloudimg-amd64.img \
  https://cloud-images.ubuntu.com/noble/current/noble-server-cloudimg-amd64.img
```

The module always reads the Ubuntu image from this exact path.

### Netropy VE 5.1.3 (from Apposite)

Obtain the Netropy VE OVA (`vn-disk1g-5.1.3.ova`) from Apposite. The OVA contains two disks;
KVM needs both converted to qcow2 with these exact names:

```bash
cd /var/lib/netropy-lab-images
tar xf /path/to/vn-disk1g-5.1.3.ova
qemu-img convert -O qcow2 vnetropy-disk1.vmdk vn-disk1g-5.1.3.qcow2
qemu-img convert -O qcow2 vnetropy-disk2.vmdk vn-disk2-256m-5.1.3.qcow2
rm -f vnetropy-disk1.vmdk vnetropy-disk2.vmdk vnetropy.ovf vnetropy.mf
ls -l
```

The CLI finds the second disk automatically when it sits next to the first one with the name
`vn-disk2-256m-5.1.3.qcow2`.

## 4. Edit the configuration file

Open `config/example-kvm.json`. This is the **only** file you need to change.

| Field | What to set |
|-------|-------------|
| `netropy_image` | Path to `vn-disk1g-5.1.3.qcow2` (default `/var/lib/netropy-lab-images/vn-disk1g-5.1.3.qcow2`) |
| `ssh_public_key_file` | Your **public** key, e.g. `~/.ssh/id_ed25519.pub` (injected into the Linux VMs) |
| `naming_prefix` | Prefix for VM/network names. Keep `netropy-lab` unless it clashes with something on the host |
| `subnets.*.cidr` | The three lab subnets. Change only if `192.168.100-102.0/24` is already used on the host |
| `instances.*` | Static IPs for each VM. Each IP must be inside its subnet; `.1` is reserved for the libvirt gateway |
| `options.vcpu`, `options.memory_mb` | Size of each **Linux** VM (Netropy sizing is fixed) |
| `options.provision_netropy` | `true` to build Netropy; `false` builds only the two Linux VMs |

Leave `platform` as `kvm` and `ubuntu_lts_version` as `24.04`. Never put passwords in this file.

## 5. Check the setup

```bash
./scripts/verify-setup.sh
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json
```

Fix every `FAIL` / `Config error` before continuing.

## 6. Create the lab

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli plan -c config/example-kvm.json   # optional preview
PYTHONPATH=cli python3 -m netropy_lab.cli up   -c config/example-kvm.json
```

`up` runs `tofu init` + `tofu apply`, then fixes storage permissions (it may ask for your
`sudo` password), sets the VMs to autostart, and prints an access summary.

Wait about **90 seconds** for cloud-init to finish on the Linux VMs, then check:

```bash
virsh -c qemu:///system list --all
ping -c 3 192.168.100.21
ssh ubuntu@192.168.100.21     # Linux-1
ssh ubuntu@192.168.100.22     # Linux-2
```

`iperf3` is pre-installed on both Linux VMs by cloud-init.

## 7. Configure Netropy (Bridging)

Netropy's web UI is HTTP on its management IP:

- On the KVM host: `http://192.168.100.10`
- From another computer, open an SSH tunnel to the KVM host first and keep it open:
  `ssh -L 8080:192.168.100.10:80 <user>@<kvm-host>`, then browse to `http://127.0.0.1:8080`

Log in with the credentials supplied with your Netropy VE image (SSH user is `admin`).
Then set:

- **Administration → Emulation Network → Bridge/Route → Forwarding Mode = Bridging**

Optional CLI check (`ssh admin@192.168.100.10`): `engine 1 show` should list `Port 1: up`,
`Port 2: up`.

## 8. Add the Linux data routes

Linux-1 and Linux-2 are on different data subnets. In Bridging mode Netropy forwards frames but
does not route, so each Linux VM needs an on-link route to the other data subnet.

**Option A — automatic (needs `ansible-core`):**

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli configure -c config/example-kvm.json
```

**Option B — manual.** On each VM, find the data NIC name first (`ip -br -4 addr`), then:

```bash
# Linux-1 (NIC that has 192.168.101.21)
sudo ip route replace 192.168.102.0/24 dev <linux1-data-nic>

# Linux-2 (NIC that has 192.168.102.22)
sudo ip route replace 192.168.101.0/24 dev <linux2-data-nic>
```

These routes are cleared when a Linux VM reboots — run this step again after a reboot.

Check the path from Linux-1:

```bash
ip route get 192.168.102.22                 # must show the data NIC, not the mgmt NIC
ping -c 4 -I 192.168.101.21 192.168.102.22
```

## 9. Send traffic through Netropy with iperf3

Always start the **server first**.

```bash
# Linux-2 — leave this running
iperf3 -s -B 192.168.102.22

# Linux-1
iperf3 -c 192.168.102.22 -B 192.168.101.21
```

The `receiver` line at the end is the throughput through Netropy. More tests (on Linux-1):

```bash
iperf3 -c 192.168.102.22 -B 192.168.101.21 -t 30          # 30-second test
iperf3 -c 192.168.102.22 -B 192.168.101.21 -R             # reverse direction
iperf3 -c 192.168.102.22 -B 192.168.101.21 -u -b 100M     # UDP: jitter + loss
```

## 10. Health check (optional)

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli verify -c config/example-kvm.json
PYTHONPATH=cli python3 -m netropy_lab.cli verify -c config/example-kvm.json --require-forwarding
```

Data-path checks report NOT READY until steps 7 and 8 are done.

## 11. Remove the lab

**This permanently deletes all three VMs, their disks, and the three lab networks.**
Your images in `/var/lib/netropy-lab-images` are kept.

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli down -c config/example-kvm.json
# type 'destroy' when prompted
```

Do not delete `modules/kvm/terraform.tfstate` while the lab exists — `down` needs it.

---

## Fallback shell scripts

If you prefer not to use the CLI (they read `config/example-kvm.json`):

```bash
cd modules/kvm
./run-apply.sh      # create / update the lab
./run-start.sh      # start stopped VMs without re-applying
./run-destroy.sh    # delete the lab (asks for confirmation)
```

`run-start.sh` and `scripts/fix-libvirt-permissions.sh` assume the default `naming_prefix`
(`netropy-lab`).

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| `Do not run netropy-lab as root or with sudo` | Run as your normal user, without `sudo` |
| `libvirt is not reachable in this shell` | Log out and back in after `usermod`, or run `newgrp libvirt` |
| `PermissionError: '/var/lib/netropy-lab-pool'` | Create the folder (step 2) |
| `netropy_image does not exist` / `netropy_config_image missing` | Check paths and exact file names from step 3 |
| `ssh_public_key_file does not exist` | Create a key (`ssh-keygen -t ed25519`) or fix the path |
| VMs do not boot / disk permission denied | `./scripts/fix-libvirt-permissions.sh` (restarts the Linux VMs) |
| `WARNING: REMOTE HOST IDENTIFICATION HAS CHANGED` after re-creating the lab | `ssh-keygen -R 192.168.100.21` (and `.22`) |
| Linux-1 cannot ping Linux-2 on the data IPs | Bridging not set (step 7) or routes missing (step 8). `ip route get 192.168.102.22` must not use the mgmt NIC |
| Netropy console shows `<<no data ports>>` | Keep the CPU/NIC/disk settings in `modules/kvm/main.tf` unchanged (host-passthrough CPU, virtio NICs, two SATA disks) |
| iperf3 `Connection refused` | The server is not running on Linux-2 — start `iperf3 -s` first |
| iperf3 `Address already in use` | A server is already running on Linux-2 — just run the client, or `pkill iperf3` and restart |
| Typed `iperf 3` and nothing connects | That starts iperf **2** on port 5001. Use `iperf3` (no space) |

## Known limitations

- **Emulation / impairments** need a valid Netropy license. Without one the UI may show
  *License Validation Failed* / Emulation OFF; Bridging still forwards traffic, so the iperf3
  path test works, but rate/delay/loss impairments do not.
- **Netropy Bridging and Linux data routes** are manual (steps 7–8); they are not applied by `up`.
- **Netropy sizing** (8 vCPU, 8 GiB) is fixed in `modules/kvm/main.tf`.
- **Ubuntu image path** is fixed at `/var/lib/netropy-lab-images/noble-server-cloudimg-amd64.img`.
