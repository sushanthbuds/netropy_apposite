# KVM E2E Acceptance Test Results

**Date:** 2026-09-11 (UTC)  
**Host:** soumi-PowerEdge-R630  
**JSON used:** `test_file/example-kvm.json` (also reachable via symlink `config/example-kvm.json` → `../test_file/example-kvm.json` for scripts that expect the old path)  
**Flow:** JSON → CLI → OpenTofu → Ansible `configure` → `verify` → iperf3 → `down`

---

## Configuration used

Canonical path for this run: **`test_file/example-kvm.json`**  
Plan path (via symlink): **`config/example-kvm.json`**

```json
{
  "platform": "kvm",
  "netropy_image": "/home/soumi/netropy-lab/Netropy-VM/vn-disk1g-5.1.3.qcow2",
  "ubuntu_lts_version": "24.04",
  "naming_prefix": "netropy-lab",
  "ssh_public_key_file": "~/.ssh/id_ed25519.pub",
  "subnets": {
    "mgmt": { "cidr": "192.168.100.0/24" },
    "data1": { "cidr": "192.168.101.0/24" },
    "data2": { "cidr": "192.168.102.0/24" }
  },
  "instances": {
    "netropy": {
      "mgmt_ip": "192.168.100.10",
      "data1_ip": "192.168.101.10",
      "data2_ip": "192.168.102.10"
    },
    "linux1": {
      "mgmt_ip": "192.168.100.21",
      "data_ip": "192.168.101.21"
    },
    "linux2": {
      "mgmt_ip": "192.168.100.22",
      "data_ip": "192.168.102.22"
    }
  },
  "options": {
    "passthrough_data_ports": false,
    "vcpu": 2,
    "memory_mb": 2048,
    "provision_netropy": true
  },
  "credentials": {
    "note": "KVM uses local libvirt. Netropy SSH user is admin; do not put passwords in this file."
  }
}
```

---

## Lab topology (reference image)

Target layout for this E2E run (management + data-1 + data-2):

![Netropy lab topology](../../project_objective/netropy-topology.svg)

**Note on E2E evidence:** this acceptance run recorded **text logs** under `/tmp/netropy-e2e-2026-09-11/` (not live PNG screenshots). Key excerpts are below.

---

## Pass/fail log

| Step | Command / action | Result | Notes |
|------|------------------|--------|-------|
| Gates | `verify-setup.sh` | PASS | After symlink restored config path |
| Gates | `check-secrets.sh` | PASS | |
| Gates | `pytest` | PASS | 48 passed |
| Validate | `cli validate -c config/example-kvm.json` | PASS | Symlink → `test_file/example-kvm.json` |
| Plan | `cli plan` | PASS | No changes while lab was up pre-destroy |
| Clean down | `cli down --yes` | PASS | Clean slate |
| Cold up | `cli up` | PASS | First attempt failed disk perms; fixed `libvirt-qemu:libvirt` + retry EXIT 0 |
| SSH ready | poll cloud-init | PASS | ~46 s |
| Configure | `cli configure` (Ansible routes) | PASS | EXIT 0; peer pings OK |
| Verify | `cli verify --require-forwarding` | PASS | Infrastructure PASS; forwarding PASS; EXIT 0 |
| iperf3 | TCP 10s Linux-1→Linux-2 via data path | PASS | See bitrate below |
| Final down | `cli down --yes` | PASS | 15 destroyed; ~11.3 s; no `netropy-lab-*` left |

---

## iperf3

| Test | Result |
|------|--------|
| TCP 10s (`-c 192.168.102.22 -B 192.168.101.21`) | **5.79 Gbits/sec** receiver; EXIT 0 |

```text
[ ID] Interval           Transfer     Bitrate         Retr
[  5]   0.00-10.00  sec  6.74 GBytes  5.79 Gbits/sec   85             sender
[  5]   0.00-10.01  sec  6.74 GBytes  5.79 Gbits/sec                  receiver
iperf Done.
IPERF_EXIT:0
```

Raw log: `/tmp/netropy-e2e-2026-09-11/10-iperf.txt`

---

## Operator notes

- Moving the JSON out of `config/` breaks `verify-setup.sh` until path is updated or a symlink is used.
- Cold `up` still often needs a one-time pool/disk ownership fix after destroy.
- Emulation-on not tested (license); Bridge path / emulation-off acceptance only.

---

## Verified / Assumed / Unknown / Needs Product Confirmation

### Verified
- Full E2E chain with this JSON succeeds including Ansible routes and strict verify.
- Teardown removes the lab.
- Document embeds the exact JSON used for the run plus the topology diagram (not the unrelated kernel-panic PNG).

### Assumed
- Symlink `config/example-kvm.json` → `test_file/example-kvm.json` is acceptable until docs/scripts are updated.
- Topology SVG plus text logs are sufficient evidence unless mentor asks for live screenshots.

### Unknown
- Whether mentor expects live UI/terminal screenshots in addition to text evidence.

### Needs Product Confirmation
- Whether Emulation-on is required for final mentor sign-off.
