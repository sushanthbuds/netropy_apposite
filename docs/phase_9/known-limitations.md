# Phase 9 — Tested Versions and Known Limitations

**Host sample (intern lab):** `soumi-PowerEdge-R630`  
**Recorded:** 2026-09-22 (validate / secrets); performance evidence 2026-09-11 — see `docs/phase_7/kvm-performance-report.md`

---

## 1. Tested versions (this host)

| Component | Version / note |
|-----------|----------------|
| OpenTofu | v1.12.4 |
| Python | 3.10.12 |
| libvirt (virsh) | 8.0.0 |
| QEMU | 6.2.0 (see Phase 7 report) |
| Ubuntu guests | 24.04 LTS cloud image |
| Netropy VE | 5.1.3 (qcow2 from OVA disk1 + disk2) |
| iperf3 (guests) | ~3.16 (Phase 7 report) |

Re-check anytime:

```bash
tofu version
python3 --version
virsh --version
./scripts/verify-setup.sh
```

---

## 2. Platform matrix

| Platform | Automate (`up`/`down`) | Manual POC | Notes |
|----------|------------------------|------------|-------|
| KVM | Yes | Yes | Primary path |
| ESXi | No (`modules/esxi/` missing) | Yes Stage A/B | Host Client; Bridging needs security Accept |

---

## 3. Known limitations

1. **Emulation / impairment** — License Validation Failed / Emulation OFF on lab appliances; path tests used Bridging with emulation off. Mentor historically accepted path-only checks.
2. **Netropy UI / credentials** — Default `admin` password is product-owned; never store in git.
3. **Data-path after `up`** — Linux on-link routes and Netropy Bridge are still manual (or optional Ansible `configure` for routes only). `verify` may report data-path NOT READY until then.
4. **ESXi automation** — CLI registers `esxi` but raises “not implemented”; Host Client–only vsphere provider limits are unknown.
5. **Passthrough** — `options.passthrough_data_ports` is schema-only (`false`); no OpenTofu path. See [passthrough-investigation.md](passthrough-investigation.md).
6. **CPU / NICs (KVM Netropy)** — Requires host-passthrough CPU, virtio × 3, both SATA disks; reinventing settings risks `<<no data ports>>` / `<<system error>>`.
7. **Do not `sudo` apply** — Breaks `$HOME` and SSH key resolution under `sg libvirt` workflows.
8. **ESXi guest IPs** — Temporary `ip addr add` clears on reboot unless netplan is applied (`docs/phase_8/netplan-examples.md`).

---

## 4. JSON / secrets reminders

- Contract: `docs/phase_4/json-field-contract.md`
- Schema: `config/lab-config.schema.json`
- Example: `config/example-kvm.json`
- `credentials.note` is documentation only — never real passwords
- Gitignore covers tfstate, tfvars generated files, large images

---

## Needs Product Confirmation

- Official Netropy VE NIC model / boot requirements on ESXi (VMXNET3 vs OVA default)
- License for Emulation ON
- Passthrough / SR-IOV support matrix for VE 5.1.3
