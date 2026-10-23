# Phase 1 — Development Instructions Guide

**Project:** Netropy VE Automated Provisioning  
**Phase:** 1 — Understand the Lab and Networking Fundamentals  
**Related write-up:** `docs/phase_1/phase1-architecture-note.md`  
**Source spec:** `project_objective/Netropy-VE-Provisioning-Intern-Project.md`  
**Topology diagram:** `project_objective/netropy-topology.svg`  

---

## 1. Purpose of Phase 1

Phase 1 is **design and learning**, not building the automation tool yet.

Before writing OpenTofu or Python code, you must understand:

1. **What the lab is for** — a repeatable Netropy VE test environment on one host  
2. **How the three VMs connect** — management vs data networks  
3. **How traffic flows** — Linux-1 → Netropy → Linux-2  
4. **What is still unknown** about Netropy VE (image, NICs, credentials)

**Exit gate (workbook):** You can explain the packet path and the role of every NIC **without reading the brief**.

Phase 1 does **not** require provisioning Netropy VE or running the full lab automation.

---

## 2. What the lab looks like (target design)

### Three virtual machines on one host

| VM | NICs | Role |
|----|------|------|
| **Netropy VE** | 1 mgmt + 2 data | Network emulator (delay, loss, bandwidth limits) |
| **Linux-1** | 1 mgmt + 1 data | Ubuntu traffic endpoint — runs **iperf3** |
| **Linux-2** | 1 mgmt + 1 data | Ubuntu traffic endpoint — other end of test path |

All test traffic stays on the host. Linux-1 and Linux-2 **do not** share a data subnet; they talk only **through Netropy**.

### Three isolated networks

| Network | CIDR (example) | Members | Purpose |
|---------|----------------|---------|---------|
| **Management** | `192.168.100.0/24` | Netropy mgmt, Linux-1 mgmt, Linux-2 mgmt | SSH, Netropy web UI / CLI |
| **Data Subnet-1** | `192.168.101.0/24` | Netropy Data Port-1, Linux-1 data NIC | Traffic from Linux-1 into emulator |
| **Data Subnet-2** | `192.168.102.0/24` | Netropy Data Port-2, Linux-2 data NIC | Traffic from emulator toward Linux-2 |

These CIDRs and IPs are reflected in `config/example-kvm.json`.

---

## 3. Seven network interfaces (the NIC table)

Phase 1 requires documenting **all seven interfaces**:

| # | VM | Interface | Subnet | Example IP |
|---|-----|-----------|--------|------------|
| 1 | Linux-1 | Mgmt | Management | `192.168.100.21` |
| 2 | Linux-1 | Data | Data Subnet-1 | `192.168.101.21` |
| 3 | Linux-2 | Mgmt | Management | `192.168.100.22` |
| 4 | Linux-2 | Data | Data Subnet-2 | `192.168.102.22` |
| 5 | Netropy VE | Mgmt | Management | `192.168.100.10` |
| 6 | Netropy VE | Data Port-1 | Data Subnet-1 | `192.168.101.10` |
| 7 | Netropy VE | Data Port-2 | Data Subnet-2 | `192.168.102.10` |

**Why this table matters:** The provisioning tool must attach each NIC to the **correct subnet** with the **correct IP**. Wrong wiring breaks the iperf3 path.

---

## 4. Traffic path (forward direction)

```
Linux-1 data (192.168.101.21)
    → Data Subnet-1
    → Netropy Data Port-1 (192.168.101.10)
    → [emulation applied inside Netropy]
    → Netropy Data Port-2 (192.168.102.10)
    → Data Subnet-2
    → Linux-2 data (192.168.102.22)
```

The **reverse path** is the same chain in the opposite direction.

The **management subnet is not used for test traffic** — only for SSH and Netropy configuration.

---

## 5. Netropy forwarding modes (user configures after provisioning)

| Mode | Layer | Beginner explanation |
|------|-------|----------------------|
| **Bridge** | Layer 2 | Forwards Ethernet frames between data ports (like a bridge) |
| **Routed** | Layer 3 | Routes IP packets between the two data subnets (like a router) |

The user chooses Bridge or Routed **after** the lab is up, via the Netropy management interface. Phase 1 automation does **not** configure emulation scenarios inside Netropy.

---

## 6. Data port considerations (why NIC type matters)

Netropy data ports use **UIO/DPDK-style** userspace I/O drivers. The Netropy software binds directly to data-port NICs for performance.

For **Phase 1 provisioning** (emulated NICs):

- Attach data ports as paravirtualized NICs (e.g. **virtio** on KVM)  
- The tool’s job is to attach the **right NIC type to the right subnet**  
- Exact NIC model and order for Netropy VE → **Needs Product Confirmation**

Optional **Phase 2 stretch goal** (project spec): passthrough data ports with host Linux bridges — not Phase 1 scope.

---

## 7. Files involved in Phase 1

| Path | Role |
|------|------|
| `project_objective/Netropy-VE-Provisioning-Intern-Project.md` | Original requirements and acceptance criteria |
| `project_objective/netropy-topology.svg` | Visual topology diagram |
| `config/example-kvm.json` | Example IPs/subnets matching the architecture |
| `docs/phase_1/phase1-architecture-note.md` | Formal Phase 1 deliverable (architecture + evidence) |
| `docs/phase_1/phase1-development-guide.md` | This guide — how Phase 1 was done |

Phase 1 is mostly **documentation and networking practice**. Code under `modules/kvm/` implements the design in later phases.

---

## 8. Hands-on networking commands (Phase 1 practice)

Use these on Linux VMs once they exist (from early KVM work or Phase 5). Phase 1 evidence often includes command output from Linux-1 and Linux-2.

### 8.1 From your host — ping management IPs

```bash
ping -c 3 192.168.100.21   # Linux-1 mgmt
ping -c 3 192.168.100.22   # Linux-2 mgmt
```

**Why:** Confirms mgmt NICs are wired to the management subnet.  
**How:** Run from the host or another VM on the same L2 domain. Success = 0% packet loss.

### 8.2 SSH into a Linux VM

```bash
ssh ubuntu@192.168.100.21
ssh ubuntu@192.168.100.22
```

**Why:** Management subnet is for admin access.  
**How:** Uses the `ubuntu` user and your SSH public key (injected later via cloud-init).

### 8.3 Inside Linux-1 or Linux-2 — inspect interfaces

```bash
ip link
ip addr
ip route
```

| Command | What it shows | Why use it |
|---------|---------------|------------|
| `ip link` | Interface names and UP/DOWN state | Verify two NICs exist (mgmt + data) |
| `ip addr` | IP addresses per interface | Confirm mgmt IP matches architecture table |
| `ip route` | Default gateway and local routes | Confirm mgmt is used for default route |

**Expected early state:** Mgmt NIC (`ens3`) UP with mgmt IP; data NIC (`ens4`) may be DOWN until full data-path setup (Phase 5).

### 8.4 VM-to-VM connectivity on management

From Linux-1:

```bash
ping -c 3 192.168.100.22
```

**Why:** Proves Linux-1 and Linux-2 can reach each other on mgmt (not through Netropy yet).

### 8.5 iperf3 basics (for later end-to-end test)

On Linux-2 (server):

```bash
iperf3 -s
```

On Linux-1 (client):

```bash
iperf3 -c 192.168.102.22 -B 192.168.101.21
```

**Why:** `-B` binds the client to Linux-1’s **data** IP so traffic uses the data path through Netropy (once Netropy is configured).  
**When:** Full path test is Phase 5; Phase 1 only needs to understand the concept.

---

## 9. Open questions to document (Needs Product Confirmation)

Phase 1 requires listing what you **assume** vs what the **product team must confirm**:

| Area | Example open questions |
|------|------------------------|
| Image & boot | Netropy qcow2 source? Minimum vCPU/RAM/disk? BIOS vs UEFI? |
| NICs | virtio OK for all three NICs? Fixed order mgmt → data1 → data2? |
| Management | Default credentials? Web UI URL? Bootstrap differs from cloud-init? |
| Traffic | Bridge vs Routed — manual only for Phase 1? Routed mode routing rules? |

Tag each item in the architecture note as **Verified**, **Assumed**, **Unknown**, or **Needs Product Confirmation**.

Do **not** invent Netropy behavior in code or docs without confirmation.

---

## 10. How Phase 1 connects to later phases

```text
Phase 1 (design)     →  config/example-kvm.json (IPs/subnets)
                    →  modules/kvm/main.tf (networks + NIC wiring)
                    →  Phase 5 (full lab + iperf3 through Netropy)
```

| Phase 1 output | Used later in |
|----------------|---------------|
| Seven-NIC table | OpenTofu network attachments in `modules/kvm/` |
| Traffic path diagram | Acceptance tests and `verify` command (Phase 7) |
| Open questions list | Questions for mentor / Travis (Netropy image, NICs) |

---

## 11. Phase 1 exit criteria (self-check)

You can mark Phase 1 complete when:

- [ ] Architecture note written (`phase1-architecture-note.md`)
- [ ] Topology diagram referenced (`netropy-topology.svg`)
- [ ] All seven NICs documented with subnet and IP
- [ ] Traffic path explained (Linux-1 → Netropy → Linux-2)
- [ ] Bridge vs Routed explained at beginner level
- [ ] Open questions listed for product team
- [ ] Hands-on evidence (ping, `ip addr`, etc.) where VMs were available
- [ ] You can explain this phase **in your own words**

---

## 12. Explain Phase 1 in your own words (student self-check)

Phase 1 was about understanding the lab before building it. I documented three VMs on three networks, seven NICs with fixed IPs, and how test traffic flows through Netropy from Linux-1 to Linux-2. I practiced basic Linux networking commands and listed what we still need to confirm with the Netropy product team. I did not build the full automation in this phase — that comes later.

---

## 13. Quick command cheat sheet

```bash
# Reachability (from host)
ping -c 3 192.168.100.21
ping -c 3 192.168.100.22

# Admin access
ssh ubuntu@192.168.100.21
ssh ubuntu@192.168.100.22

# Inside a Linux VM
ip link
ip addr
ip route
ping -c 3 192.168.100.22   # from Linux-1 to Linux-2 mgmt

# Traffic test (after Netropy configured — Phase 5)
# On Linux-2:  iperf3 -s
# On Linux-1:  iperf3 -c 192.168.102.22 -B 192.168.101.21
```

---

**Document status:** Development instructions for Phase 1 (intern reference).  
**Do not commit:** secrets, private keys, or screenshots containing credentials.
