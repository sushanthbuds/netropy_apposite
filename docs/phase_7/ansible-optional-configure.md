# Optional Ansible — Post-Up Data Routes

**Project:** Netropy VE Automated Provisioning  
**Related:** `ansible/`, CLI `configure`  
**Objective reference:** optional Ansible alongside OpenTofu/cloud-init (§6.1–6.2)

---

## Purpose

After `netropy-lab up`, Linux-1 and Linux-2 still need **on-link routes** to the peer data subnet so traffic can reach the other endpoint through Netropy (Phase 5 manual `ip route replace` steps).

Optional Ansible automates those Linux routes only.

| Does | Does not |
|------|----------|
| Add peer data routes via SSH | Replace OpenTofu / cloud-init |
| Detect data NIC by IP | Configure Netropy Bridge/Route UI |
| Support re-run (`ip route replace`) | Store Netropy or host passwords |
| KVM first | Phase-2 PCI passthrough / host bridge |

---

## Prerequisites

1. Lab provisioned and SSH working:
   ```bash
   ssh ubuntu@192.168.100.21
   ssh ubuntu@192.168.100.22
   ```
2. `ansible-playbook` on the provisioning host:
   ```bash
   sudo apt install -y ansible-core
   # or: pip install --user ansible-core
   ```
3. Wait ~90 seconds after `up` for cloud-init.

If VMs were recreated, clear stale host keys:

```bash
ssh-keygen -R 192.168.100.21
ssh-keygen -R 192.168.100.22
```

---

## Recommended flow

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli up -c config/example-kvm.json
# wait for cloud-init
PYTHONPATH=cli python3 -m netropy_lab.cli configure -c config/example-kvm.json
PYTHONPATH=cli python3 -m netropy_lab.cli verify -c config/example-kvm.json --require-forwarding
```

`configure`:

1. Validates the JSON (KVM only)
2. Writes `ansible/inventory/lab.generated.ini` (gitignored)
3. Runs `ansible/playbooks/configure-routes.yml`
4. Pings each peer data IP (fails if Netropy is not bridging yet)

Netropy Bridge/Route may still need a one-time setup in the product UI/CLI. Ansible only handles Linux routes.

---

## Standalone Ansible

```bash
cd ansible
ansible-playbook -i inventory/lab.generated.ini playbooks/configure-routes.yml
```

Generate the inventory first with `netropy-lab configure` (or write the INI by hand using the same host vars).

---

## Layout

| Path | Role |
|------|------|
| `ansible/ansible.cfg` | Local defaults (`host_key_checking=False`) |
| `ansible/playbooks/configure-routes.yml` | Route + peer ping tasks |
| `ansible/inventory/lab.generated.ini` | Generated; not committed |
| `cli/netropy_lab/ansible_inv.py` | JSON → inventory |
| `cli/netropy_lab/cli.py` | `configure` command |

---

## Secrets

- Do not put Netropy passwords in playbooks, inventory, or git.
- SSH uses the same key injected by cloud-init (`ssh_public_key_file` in JSON).

---

## Verified / Assumed / Unknown / Needs Product Confirmation

### Verified

- Phase 5 path needs on-link routes for cross-subnet data traffic.
- Project objective lists Ansible as optional beside OpenTofu/cloud-init.

### Assumed

- Guests allow passwordless `sudo` for `ubuntu` (cloud-init lab default).

### Unknown

- Whether ESXi will reuse this playbook unchanged.

### Needs Product Confirmation

- Automating Netropy Bridge via API/CLI (out of scope here).
