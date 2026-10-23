# Phase 8 — Persistent IPs (netplan examples)

Manual `ip addr add` is cleared on reboot. After Stage B works, put these on the Linux VMs (adjust `ens*` names to match **ESXi Edit → Network adapters** order).

Do **not** commit live passwords. Apply on the guests only.

---

## linux1 (`sushanth-linux1`)

Example when adapter1 = `sushanth-mgmt`, adapter2 = `sushanth-data1`, adapter3 = `VM Network`:

```yaml
# /etc/netplan/99-netropy-lab.yaml
network:
  version: 2
  ethernets:
    ens160:
      addresses: [192.168.100.21/24]
    ens192:
      addresses: [192.168.101.21/24]
      routes:
        - to: 192.168.102.0/24
          scope: link
    ens224:
      dhcp4: true   # VM Network for apt/SSH from Windows; omit if unused
```

```bash
sudo netplan apply
```

---

## linux2 (`sushanth-linux2`)

Example when adapter1 = `sushanth-data2`, adapter2 = `sushanth-mgmt`, adapter3 = `VM Network`:

```yaml
# /etc/netplan/99-netropy-lab.yaml
network:
  version: 2
  ethernets:
    ens160:
      addresses: [192.168.102.22/24]
      routes:
        - to: 192.168.101.0/24
          scope: link
    ens192:
      addresses: [192.168.100.22/24]
    ens224:
      dhcp4: true
```

```bash
sudo netplan apply
```

---

## Netropy mgmt (CLI — survives if saved in appliance config)

```text
mgmt set addr 192.168.100.10 netmask 255.255.255.0
mgmt show
```

Use UI **Engine Configurations → Save** if the product requires an explicit save after changes.

---

## Reminder

Re-check adapter ↔ port group in ESXi before copying these files. Wrong `ens*` assignment breaks the path again.
