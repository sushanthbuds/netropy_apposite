# Setup demo topology for Netropy WAN Emulator in ESXi

This guide builds a small Netropy VE demo lab on a **standalone ESXi host** using the
**ESXi Host Client** (browser UI, no vCenter). The ESXi steps are manual. All names and IP
addresses come from **one file**, `lab-parameters.json`. A helper script turns that file into
the guest network configs, so you never type IPs in more than one place.

| VM | Network adapters | Role |
|----|------------------|------|
| Netropy VE | mgmt + data-1 + data-2 | WAN emulator (bridges data-1 ↔ data-2) |
| Linux-1 (Ubuntu 24.04) | mgmt + data-1 + internet | iperf3 client |
| Linux-2 (Ubuntu 24.04) | mgmt + data-2 + internet | iperf3 server |

Three isolated networks (vSwitch + port group each): **mgmt**, **data-1**, **data-2**.
Traffic from Linux-1 to Linux-2 on the data networks must pass through Netropy.
Diagram: [`docs/netropy-topology.svg`](docs/netropy-topology.svg).

Default addresses (edit `lab-parameters.json` to change them):

| Host | mgmt | data |
|------|------|------|
| Netropy VE | `192.168.100.10` | none needed (Bridging) |
| Linux-1 | `192.168.100.21` | `192.168.101.21` |
| Linux-2 | `192.168.100.22` | `192.168.102.22` |

---

## Package contents

| Path | Purpose |
|------|---------|
| `lab-parameters.json` | **The only file you edit** — names, datastore, subnets, IPs, Linux NIC names |
| `render-configs.py` | Validates the parameters and writes the files in `output/` (Python 3, no extra packages) |
| `output/` | Created by the script: netplan files for both Linux VMs, iperf3 service, Netropy console command |
| `docs/netropy-topology.svg` | Topology diagram |

The Netropy VE OVA and the Ubuntu ISO are **not** included.

---

## 1. Requirements

- A standalone ESXi host and a login for the **Host Client** (`https://<esxi-host-ip>/ui`).
  Tested with the ESXi Host Client (no vCenter). Company VPN may be required.
- A datastore with about **60 GiB** free (two Ubuntu desktop VMs + Netropy).
- An existing port group with **DHCP and internet** (usually `VM Network`). The Linux VMs use it
  to install packages and for SSH from your computer.
- **Ubuntu 24.04 ISO** (desktop ISO was tested; server ISO also works — see step 1).
- **Netropy VE 5.1.3 OVA** (`vn-disk1g-5.1.3.ova`) from Apposite.
- **Python 3** on the computer where you run `render-configs.py` (any OS; Ubuntu has it built in).

Never write the ESXi or Netropy passwords into any file in this package.

## 2. Fill in the parameters and render the configs

Edit `lab-parameters.json`:

| Field | What to set |
|-------|-------------|
| `naming_prefix` | Prefix for every vSwitch, port group, and VM. Pick something unique on the host (e.g. your name) so you never touch other people's resources |
| `esxi.host`, `esxi.datastore` | Your ESXi host IP and the datastore to use |
| `esxi.ubuntu_iso` | Datastore path of the Ubuntu ISO after upload (step 4) |
| `esxi.netropy_ova` | File name of the Netropy OVA on your computer |
| `esxi.internet_port_group` | Existing port group with DHCP + internet (default `VM Network`) |
| `subnets.*.cidr` | The three lab subnets (network address, e.g. `192.168.101.0/24`) |
| `instances.*` | Static IPs; each must be inside its subnet |
| `linux_guest.*_nic` | Linux NIC names for adapter 1 / 2 / 3. `ens160` / `ens192` / `ens224` is what Ubuntu shows for VMXNET3 adapters 1–3; confirm in step 6 |
| `linux_guest.netplan_renderer` | `NetworkManager` for Ubuntu **Desktop**, `networkd` for Ubuntu **Server** |

Then run:

```bash
python3 render-configs.py
```

It checks the values (IPs inside subnets, no duplicates, no overlapping subnets) and prints the
exact names to use in the Host Client. Keep that output open while you work through the next
steps. Re-run the script any time you change `lab-parameters.json`.

## 3. Create the networks

Do this three times — for **mgmt**, **data1**, and **data2** — using the names printed by the script.

1. **Networking → Virtual switches → Add standard virtual switch**
   - Name: `vSwitch-<prefix>-<network>`
   - Remove the **Uplink** entry, so the switch has **no physical uplink** (isolated lab network).
   - Under **Security**, set **Promiscuous mode**, **MAC address changes**, and
     **Forged transmits** to **Accept**.
2. **Networking → Port groups → Add port group**
   - Name: `<prefix>-<network>`, virtual switch: the one you just created.
   - Security: inherit from the vSwitch (or set the same three options to **Accept**).

The three **Accept** settings are required on data-1 and data-2. Without them the Netropy
bridge does not pass traffic.

## 4. Upload the Ubuntu ISO

**Storage → `<datastore>` → Datastore browser → Create directory** `iso`, then **Upload** the
Ubuntu ISO into it. The path must match `esxi.ubuntu_iso`.

## 5. Create Linux-1 and Linux-2

For each Linux VM: **Virtual Machines → Create / Register VM → Create a new virtual machine**.

| Setting | Value |
|---------|-------|
| Name | `<prefix>-linux1` / `<prefix>-linux2` |
| Guest OS | Linux → **Ubuntu Linux (64-bit)** |
| Storage | your datastore |
| CPU / Memory / Disk | 2 vCPU, 4 GB, 25 GB (Desktop ISO minimum; Server ISO can use less) |
| **Network Adapter 1** | `<prefix>-mgmt` |
| **Network Adapter 2** | Linux-1: `<prefix>-data1` — Linux-2: `<prefix>-data2` |
| **Network Adapter 3** | internet port group (e.g. `VM Network`) |
| Adapter type | VMXNET 3 (default) |
| CD/DVD | Datastore ISO file → the Ubuntu ISO, **Connect at power on** |

Use this adapter order on **both** VMs — the generated netplan files expect it.

Power on, open the console, and install Ubuntu (create a user and password). After the first
boot, open a terminal and install the tools:

```bash
sudo apt update
sudo apt install -y iperf3 openssh-server
```

If the iperf3 installer asks *"Start Iperf3 as a daemon automatically?"*, answer **No**.

## 6. Confirm the NIC names

On each Linux VM:

```bash
ip -br link
```

In the Host Client, open the VM → **Edit** and compare each **Network Adapter**'s MAC address
with the list. The expected result is:

| ESXi adapter | Linux NIC | Port group |
|--------------|-----------|------------|
| Network Adapter 1 | `ens160` | `<prefix>-mgmt` |
| Network Adapter 2 | `ens192` | `<prefix>-data1` (Linux-1) / `<prefix>-data2` (Linux-2) |
| Network Adapter 3 | `ens224` | internet port group |

If your names differ, put the real names in `linux_guest` and re-run `render-configs.py`.

## 7. Give the Linux VMs static IPs (netplan)

Do this on **Linux-1** with `output/linux1-netplan.yaml` and on **Linux-2** with
`output/linux2-netplan.yaml`.

```bash
# Move the existing netplan files out of the way (keeps a backup in /root)
ls /etc/netplan/
sudo mv /etc/netplan/*.yaml /root/

# Create the new file — note the sudo
sudo nano /etc/netplan/01-netropy-lab.yaml
```

Paste the full contents of the generated file (**Ctrl+Shift+V** in a terminal), save with
**Ctrl+O**, **Enter**, and exit with **Ctrl+X**. Then:

```bash
sudo chmod 600 /etc/netplan/01-netropy-lab.yaml
ls /etc/netplan/          # must list exactly one .yaml file
sudo netplan try          # press Enter to keep the new settings
ip -4 addr show
ip route
```

You can also copy the file over SSH instead of pasting (use the VM's internet IP from
`ip -4 addr show ens224`).

Expected on Linux-1: `192.168.100.21` on the mgmt NIC, `192.168.101.21` on the data NIC, and a
route `192.168.102.0/24 dev <data NIC> ... scope link`. Linux-2 is the mirror image.
These settings survive reboots.

## 8. Deploy Netropy VE from the OVA

**Virtual Machines → Create / Register VM → Deploy a virtual machine from an OVF or OVA file**

- Name: `<prefix>-netropy`
- Select the OVA file (`esxi.netropy_ova`)
- Storage: your datastore
- **Network mappings** (source names come from the OVA):

  | OVA network | Map to |
  |-------------|--------|
  | `VM Network` | `<prefix>-mgmt` |
  | `TestNetwork-1` | `<prefix>-data1` |
  | `TestNetwork-2` | `<prefix>-data2` |

- Keep all other settings at the OVA defaults and finish. Power on the VM.

## 9. Set the Netropy management IP

The mgmt network has no DHCP, so Netropy starts with a `169.254.x.x` address. Open the Netropy
VM **console** in the Host Client, log in with the credentials supplied with your Netropy image
(user `admin`), and run the commands from `output/netropy-console.txt`:

```text
mgmt set addr 192.168.100.10 netmask 255.255.255.0
mgmt show
```

## 10. Enable Bridging in the Netropy web UI

The web UI is HTTP on the Netropy mgmt IP, which is only reachable from the lab mgmt network.
From your computer, tunnel through Linux-1 (its internet IP from `ip -4 addr show ens224`) and
keep this SSH session open:

```bash
ssh -L 8080:192.168.100.10:80 <linux1-user>@<linux1-internet-ip>
```

Browse to `http://127.0.0.1:8080`, log in, and set:

- **Administration → Emulation Network → Bridge/Route → Forwarding Mode = Bridging**
- Keep the ports on **Bypass** (not **Drop**)

Optional CLI check over SSH (`ssh admin@192.168.100.10` from Linux-1): `engine 1 show` should
list `Port 1: up` and `Port 2: up`.

## 11. Check the path

On **Linux-1**:

```bash
ping -c 4 192.168.100.22                    # Linux-2 mgmt (does not use Netropy)
ping -c 4 192.168.100.10                    # Netropy mgmt
ip route get 192.168.102.22                 # must show the data NIC (ens192), not ens224
ping -c 4 -I 192.168.101.21 192.168.102.22  # Linux-2 data, through Netropy
```

## 12. Send traffic through Netropy with iperf3

Always start the **server first**.

```bash
# Linux-2 — leave this running
iperf3 -s -B 192.168.102.22

# Linux-1
iperf3 -c 192.168.102.22 -B 192.168.101.21
```

The `receiver` line is the throughput through Netropy. More tests (on Linux-1):

```bash
iperf3 -c 192.168.102.22 -B 192.168.101.21 -t 30          # 30-second test
iperf3 -c 192.168.102.22 -B 192.168.101.21 -R             # reverse direction
iperf3 -c 192.168.102.22 -B 192.168.101.21 -u -b 100M     # UDP: jitter + loss
```

**Optional — start the iperf3 server automatically on Linux-2** (then only the client command
is needed):

```bash
sudo nano /etc/systemd/system/iperf3-lab.service   # paste output/iperf3-lab.service
sudo systemctl daemon-reload
sudo systemctl enable --now iperf3-lab
ss -ltnp | grep 5201
```

A background server prints nothing; watch it with `journalctl -u iperf3-lab -f`.

## 13. Optional: power on the lab with the host

**Host → Manage → System → Autostart → Edit settings → Enabled**, then for each lab VM
(Netropy first): **Actions → Autostart → Enable**. Menu names can differ slightly between ESXi
versions.

---

## Troubleshooting

| Symptom | Cause / fix |
|---------|-------------|
| `render-configs.py` prints `Parameter error: ...` | Fix the named field in `lab-parameters.json`. Subnets must be network addresses (`192.168.101.0/24`, not `192.168.101.21/24`) |
| nano: `Error writing ... Permission denied` | You opened the file without `sudo`. Exit without saving (**Ctrl+X**, **N**) and use `sudo nano` |
| netplan warns `Permissions ... are too open` | `sudo chmod 600 /etc/netplan/*.yaml` (warning only) |
| Wrong or duplicate routes after `netplan apply` | More than one file in `/etc/netplan/` (e.g. a mistyped file name). Keep exactly one `.yaml` file |
| `ping -I 192.168.101.21 ...`: `Cannot assign requested address` | The data IP is not configured — redo step 7 |
| `ip route get 192.168.102.22` shows `ens224` / `via <gateway>` | Missing on-link route on Linux-1 — the data NIC route must be `to: 192.168.102.0/24` |
| Mgmt ping works, data ping fails, `tcpdump -ni <data NIC>` on Linux-2 shows nothing | Netropy not in Bridging, ports on Drop, OVA networks mapped wrong (step 8), or the three **Accept** settings missing (step 3) |
| Netropy shows `169.254.x.x` | Management IP not set — step 9 |
| iperf3 `Connection refused` | Server not running on Linux-2 (the path itself works). Start `iperf3 -s` first |
| iperf3 `Address already in use` | A server is already running (e.g. the systemd service). Just run the client |
| Typed `iperf 3` and nothing connects | That starts iperf **2** on port 5001. Use `iperf3` (no space) |
| Ports shown as `ens3`/`enp...` or in a different order | Put the real names in `linux_guest` and re-render (step 6) |

## Cleanup

Only delete resources that use **your** `naming_prefix` — do not touch other users' VMs.

1. Power off and delete the three VMs: **Actions → Delete** (removes their disks).
2. **Networking → Port groups**: remove `<prefix>-mgmt`, `<prefix>-data1`, `<prefix>-data2`.
3. **Networking → Virtual switches**: remove the three `vSwitch-<prefix>-*` switches.

## Known limitations

- **Manual build:** there are no Terraform/OpenTofu scripts for ESXi yet; the KVM package is the
  automated version of this lab.
- **Emulation / impairments** need a valid Netropy license. Without one the UI may show
  *License Validation Failed* / Emulation OFF; Bridging still forwards traffic, so the iperf3
  path test works, but rate/delay/loss impairments do not.
- **Netropy settings after reboot:** whether the mgmt IP and Bridging mode persist without an
  explicit save is not confirmed — re-check steps 9–10 after restarting Netropy.
- **Netropy VM sizing and NIC model** use the OVA defaults; official ESXi sizing guidance comes
  from Apposite.
