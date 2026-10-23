# KVM Lab Performance and Acceptance Report

**Project:** Netropy VE Automated Provisioning  
**Scope:** Phases 1–7 on KVM only  
**Host:** `soumi-PowerEdge-R630`  
**Date of run:** 2026-09-11 (UTC)  
**Config:** `config/example-kvm.json`  
**Netropy VE:** 5.1.3  

---

## 1. Purpose

This report measures **automation timing** and **data-path throughput** for the existing KVM lab (OpenTofu + Python CLI + Netropy VE + two Ubuntu endpoints). It is an **acceptance / performance evidence** package for mentor handover.

It is **not**:

- A licensed Netropy impairment certification (Emulation on)
- An ESXi result
- A new test framework (reuses `pytest`, `validate`, `verify`, and manual iperf3)

---

## 2. Environment

| Item | Value |
|------|-------|
| Hostname | soumi-PowerEdge-R630 |
| CPU | Intel Xeon E5-2695 v4 @ 2.10GHz (2 sockets × 18 cores × 2 threads = 72 logical CPUs) |
| RAM | 251 GiB |
| Root disk free | ~830 GiB on `/` |
| OpenTofu | v1.12.4 |
| Python | 3.10.12 |
| libvirt / QEMU | libvirt 8.0.0, QEMU 6.2.0 |
| Ubuntu guests | 24.04 LTS cloud image + iperf3 3.16 |
| Concurrent host VMs during test | `netropy-poc-ubuntu`, `ot-conn-vm-1`, `ot-conn-vm-2` (all shut off) |

### Lab addressing (from JSON)

| Role | Mgmt IP | Data IP(s) |
|------|---------|------------|
| Netropy | 192.168.100.10 | 192.168.101.10 / 192.168.102.10 |
| Linux-1 | 192.168.100.21 | 192.168.101.21 |
| Linux-2 | 192.168.100.22 | 192.168.102.22 |

**Traffic path under test:** Linux-1 data → Netropy Port 1 → Netropy Port 2 → Linux-2 data (Bridge path, emulation off).

---

## 3. Method

1. Host gates: `./scripts/verify-setup.sh`, `./scripts/check-secrets.sh`
2. Unit/config: `pytest` in `cli/`, `netropy-lab validate`
3. Timed `down` (clean slate), timed `up`, poll SSH until both Linux guests ready
4. `netropy-lab verify` then `verify --require-forwarding`
5. On-link data routes on Linux guests (Phase 5 procedure); data-path verify PASS
6. iperf3 matrix T1–T5 and ping P1 through the data path
7. Timed idempotent `up` (expect no changes) and final timed `down`

Raw outputs retained on the host under `/tmp/netropy-perf-2026-09-11/` (not committed).

---

## 4. Gate results

| Check | Result |
|-------|--------|
| `verify-setup.sh` | PASS (cloud-init host package WARN only) |
| `check-secrets.sh` | PASS |
| `pytest` (`cli/`) | **43 passed** in 0.49s |
| `validate` | PASS |

---

## 5. Provisioning / teardown timing

| Operation | Wall time | Notes |
|-----------|-----------|-------|
| Pre-run `down` (existing lab) | **13.72 s** | 13 resources destroyed |
| Cold `up` attempt #1 | 15.02 s | **Failed:** QEMU permission denied on pool disks (`root:root` mode `600`) after pool dir recreate |
| Permission fix | manual | `chown libvirt-qemu:libvirt` + `chmod 660` on `/var/lib/netropy-lab-pool/*` |
| Cold `up` attempt #2 (domains) | **11.70 s** | Volumes/networks already present; 3 domains created; EXIT 0 |
| Time to SSH + cloud-init done (both Linux) | **~44 s** | After successful `up` |
| `verify` (infra; before forwarding) | 10.33 s | Infrastructure PASS; data-path NOT READY until routes |
| `verify --require-forwarding` | **10.52 s** | EXIT 0; Infrastructure PASS; forwarding PASS |
| Idempotent `up` | **7.42 s** | `No changes` / 0 added, 0 changed, 0 destroyed |
| Final `down` | **11.19 s** | 15 resources destroyed; lab VMs absent from `virsh list --all` |

**Operator note:** After a full destroy, `/var/lib/netropy-lab-pool` may need recreating and ownership fixed before the next cold `up`, or the first apply can define volumes that QEMU cannot read until permissions are corrected.

**SSH note:** Recreating VMs changes guest host keys. Stale `~/.ssh/known_hosts` entries caused a temporary `verify` SSH FAIL until keys were removed/re-accepted.

---

## 6. Data-path setup

- Linux-1: `sudo ip route replace 192.168.102.0/24 dev ens4`
- Linux-2: `sudo ip route replace 192.168.101.0/24 dev ens4`
- After routes, peer data pings succeeded and `verify --require-forwarding` passed
- Emulation remained **off** (license not used for impairment tests)

Netropy web UI responded HTTP 200 on `http://192.168.100.10`. Login user is product default `admin`; **password is not stored in this document or in git**.

---

## 7. Throughput and latency results

All iperf3 client runs from Linux-1 bound to `192.168.101.21` toward Linux-2 `192.168.102.22` with `iperf3 -s` on Linux-2.

| ID | Test | Result |
|----|------|--------|
| T1 | TCP 10 s | **7.12 Gbits/sec** receiver |
| T2 | TCP 60 s | **6.89 Gbits/sec** receiver |
| T3 | TCP reverse 10 s (`-R`) | **8.18 Gbits/sec** receiver |
| T4 | TCP 4 streams × 30 s | **7.30 Gbits/sec** SUM receiver |
| T5 | UDP `-b 1G` × 20 s | Sender 1000 Mbits/sec; receiver **901 Mbits/sec**, **9.9%** datagram loss |
| P1 | `ping -c 20` peer data IP | **0% loss**; rtt min/avg/max = **0.372 / 0.593 / 0.779 ms** |

### Comparison to prior Phase 5 note

Phase 5 (`docs/phase_5/phase5-development-guide.md`, 2026-08-27) recorded ~**7 Gbit/s** for a short Bridge / emulation-off iperf3 run. This suite’s T1 (**7.12 Gbit/s**) and T2 (**6.89 Gbit/s**) are consistent with that baseline on the same host class of path.

High bitrates indicate **emulation impairments are off**. Traffic still crosses Netropy’s two data ports.

---

## 8. Limitations

- **Emulation on** (delay/loss/rate-limit) not executed — prior Phase 5 guidance: license validation failed on this lab; mentor accepted path test with emulation off
- On-link data routes are still **manual** after boot
- Cold `up` timing was split by a **pool permission** incident; report numbers reflect measured segments, not a single uninterrupted `time up` from empty pool
- Single-host KVM only; no ESXi numbers
- Host load / NIC virtio limits can skew Gbit/s; treat as lab evidence, not a product datasheet

---

## 9. Conclusions

1. Phase 1–7 KVM automation **gates pass** (setup, secrets, 43 unit tests, validate).
2. Lab **create / verify / destroy** work end-to-end; idempotent `up` is a no-op (~7 s).
3. Data path through Netropy in Bridge / emulation-off mode sustains roughly **7 Gbit/s** TCP and sub-millisecond ping RTT on this host.
4. Operational friction remains around **libvirt pool permissions after destroy** and **SSH known_hosts** after recreate — document for operators; not a topology failure.
5. Ready for mentor review of KVM acceptance while ESXi access is pending.

**Mentor question:** Is Emulation-on with a valid license required for final sign-off, or is Bridge / emulation-off path proof sufficient?

---

## 10. Appendix — trimmed command index

```bash
./scripts/verify-setup.sh
./scripts/check-secrets.sh
cd cli && PYTHONPATH=. pytest -q
PYTHONPATH=cli python3 -m netropy_lab.cli validate -c config/example-kvm.json
PYTHONPATH=cli python3 -m netropy_lab.cli down -c config/example-kvm.json --yes
PYTHONPATH=cli python3 -m netropy_lab.cli up -c config/example-kvm.json
PYTHONPATH=cli python3 -m netropy_lab.cli verify -c config/example-kvm.json --require-forwarding
# Linux-1 / Linux-2 on-link routes (Phase 5)
# iperf3 -s on Linux-2; iperf3 client matrix on Linux-1
PYTHONPATH=cli python3 -m netropy_lab.cli down -c config/example-kvm.json --yes
```

Raw logs: `/tmp/netropy-perf-2026-09-11/` (`T1`…`T5`, `P1`, verify/up/down transcripts).

---

## Verified / Assumed / Unknown / Needs Product Confirmation

### Verified

- 43 `pytest` tests pass; validate and setup scripts pass on this host
- Three lab VMs provision and destroy via CLI; forwarding verify PASS after routes
- iperf3 TCP ~7 Gbit/s class throughput and ~0.6 ms avg ping on the data path (emulation off)
- Final `down` removes lab domains from libvirt

### Assumed

- Mentor still accepts emulation-off Bridge path as the KVM traffic proof
- Concurrent shut-off VMs on the host did not materially invalidate results

### Unknown

- Whether pool-permission fix should be automated into `up` without interactive sudo
- Whether cloud-init should install the on-link data routes by default

### Needs Product Confirmation

- Official VE 5.1.3 license requirement for **Emulation on** sign-off
- Whether final handover requires impairment demos beyond path throughput

---

**Do not commit:** secrets, Netropy/host passwords, `*.tfstate`, or `lab.auto.tfvars.json`.
