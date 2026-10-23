# Optional Ansible — post-up data routes

Adds the on-link peer data routes on Linux-1 and Linux-2 after `netropy-lab up`.
This is the same effect as the manual Phase 5 `ip route replace` steps.

OpenTofu + cloud-init still create the VMs. Ansible does **not** replace them.
Ansible does **not** configure Netropy Bridge/Route or store Netropy passwords.

## Prerequisites

- Lab already up and SSH working: `ssh ubuntu@<linux-mgmt-ip>`
- `ansible-playbook` on the provisioning host (`ansible-core` or `ansible`)

```bash
sudo apt install -y ansible-core   # or: pip install --user ansible-core
```

## Preferred: CLI

From the repo root (after cloud-init finishes, ~90s):

```bash
PYTHONPATH=cli python3 -m netropy_lab.cli configure -c config/example-kvm.json
PYTHONPATH=cli python3 -m netropy_lab.cli verify -c config/example-kvm.json --require-forwarding
```

## Standalone playbook

```bash
# Generate inventory via CLI helper, or write inventory/lab.generated.ini yourself
PYTHONPATH=cli python3 -m netropy_lab.cli configure -c config/example-kvm.json
# configure already runs the playbook; for a re-run only:
cd ansible
ansible-playbook -i inventory/lab.generated.ini playbooks/configure-routes.yml
```

## Notes

- Data NIC is detected by matching `data_ip` (not hardcoded `ens4`).
- After VM recreate, clear stale SSH host keys: `ssh-keygen -R <mgmt-ip>`
- Generated inventory `inventory/lab.generated.ini` is gitignored.

See `docs/phase_7/ansible-optional-configure.md`.
