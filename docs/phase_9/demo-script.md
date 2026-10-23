# Phase 9 — Demo Script (KVM)

**Audience:** Mentor / new operator  
**Goal:** Build → access → verify → (optional path test) → destroy from a clean start  
**Config:** `config/example-kvm.json`  
**Do not use `sudo`.** Do not paste passwords into chat or git.

---

## Before you start

1. User is in group `libvirt`; `kvm-ok` passes.
2. Ubuntu cloud image exists at `/var/lib/netropy-lab-images/noble-server-cloudimg-amd64.img`.
3. Netropy qcow2 pair under `Netropy-VM/` (disk1 + sibling disk2).
4. `ssh_public_key_file` in JSON points at your **public** key.
5. From repo root:

```bash
./scripts/verify-setup.sh
./scripts/check-secrets.sh
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json
```

---

## Script (talk track)

### A. Show the recipe (1 min)

- One JSON file describes platform, subnets, IPs, image paths.
- CLI: `validate` → `plan` → `up` → `verify` → `down`.
- Topology: Netropy + Linux-1 + Linux-2 on mgmt / data1 / data2.

### B. Plan (optional, ~1–2 min)

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli plan -c config/example-kvm.json
```

### C. Build (idempotent apply)

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli up -c config/example-kvm.json
```

Wait ~90 seconds for cloud-init. Note printed SSH targets.

**Idempotent re-run (optional):** run `up` again — should converge without recreating from scratch unnecessarily.

### D. Access summary

```bash
ssh ubuntu@192.168.100.21
ssh ubuntu@192.168.100.22
# Netropy: ssh admin@192.168.100.10  (password not in git)
```

**Netropy web UI**

| Where you browse | How |
|------------------|-----|
| On the KVM host (PowerEdge) | Open `http://192.168.100.10` (port 80). This IP is only on the lab mgmt network — Windows cannot open it directly. |
| From Windows / remote PC | Tunnel, leave SSH open, then open `http://127.0.0.1:8080`: |

```powershell
ssh -L 8080:192.168.100.10:80 soumi@10.0.0.7
```

(Use the PowerEdge’s real address if it differs from `10.0.0.7` on your network.)

After every recreate, if SSH complains about host keys:

```bash
ssh-keygen -R 192.168.100.21
ssh-keygen -R 192.168.100.22
```

### E. Verify (infrastructure)

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli verify -c config/example-kvm.json
```

Expect **Infrastructure: PASS**. **Netropy forwarding: NOT READY** is normal until section F.

### F. Data path — Bridge + on-link routes (required for forwarding PASS / iperf3)

Automation does **not** configure Netropy Bridging or guest data routes. Do this before `--require-forwarding` or a live iperf3 demo.

#### F1. Netropy Bridging (UI)

1. Open the UI (section D).
2. **Administration → Emulation Network → Bridge/Route → Forwarding Mode = Bridging**
3. Apply/save if the UI asks. Keep **Bypass** (not Drop) on ports if shown.
4. Emulation ON / impairment may fail license — path test with emulation off is OK (**Needs Product Confirmation** for license).

#### F2. On-link routes on Linux guests

Data NICs sit on different /24s. Add routes so each guest sends peer-subnet traffic out its data NIC (through Netropy).

```bash
# Confirm which interface holds the data IP (often ens4)
ssh ubuntu@192.168.100.21 "ip -br addr"
ssh ubuntu@192.168.100.22 "ip -br addr"
```

Replace `ens4` below if your data NIC name differs:

```bash
# Linux-1: reach Linux-2 data subnet via data NIC
ssh ubuntu@192.168.100.21 "sudo ip route replace 192.168.102.0/24 dev ens4"

# Linux-2: reach Linux-1 data subnet via data NIC
ssh ubuntu@192.168.100.22 "sudo ip route replace 192.168.101.0/24 dev ens4"
```

Optional (routes only — still need Bridging in the UI):

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli configure -c config/example-kvm.json
```

Quick check:

```bash
ssh ubuntu@192.168.100.21 "ping -c 2 192.168.102.22"
```

Routes from `ip route replace` clear on guest reboot — re-add or use `configure` again.

#### F3. Verify forwarding + optional iperf3

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli verify -c config/example-kvm.json --require-forwarding
```

iperf3 (mentor time permitting):

```bash
# Linux-2
ssh ubuntu@192.168.100.22 "iperf3 -s"

# Linux-1 (other terminal)
ssh ubuntu@192.168.100.21 "iperf3 -c 192.168.102.22 -B 192.168.101.21"
```

More detail: `docs/phase_5/phase5-development-guide.md`.

### G. Destroy (clean teardown)

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli down -c config/example-kvm.json
# type destroy when prompted, or --yes
```

Confirm VMs gone:

```bash
virsh -c qemu:///system list --all
```

---

## Troubleshooting (short)

| Symptom | Check |
|---------|--------|
| Permission / pool errors | Create/fix pool: `sudo mkdir -p /var/lib/netropy-lab-pool` then `./scripts/fix-libvirt-permissions.sh` |
| Netropy no data ports | Two SATA disks, virtio NICs, host-passthrough CPU — Phase 5 guide |
| `verify` SSH key failed after recreate | `ssh-keygen -R 192.168.100.21` (and `.22`); not a wrong JSON key |
| `verify` data-path NOT READY | Do section F (Bridging + on-link routes); expected before that |
| Windows can’t open `192.168.100.10` | Use SSH tunnel → `http://127.0.0.1:8080` (section D) |
| Accidental root apply | Never use `sudo` for `up`/`down` — breaks `$HOME` / SSH key paths |

---

## ESXi (mention only)

- **ESXi:** manual Stage A/B proven — `docs/phase_8/`; no `netropy-lab up -c esxi` yet.
