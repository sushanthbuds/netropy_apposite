terraform {
  required_version = ">= 1.6.0"

  required_providers {
    libvirt = {
      source  = "dmacvicar/libvirt"
      version = "~> 0.9"
    }
  }
}

provider "libvirt" {
  uri = "qemu:///system"
}

locals {
  project_root = abspath("${path.module}/..")
  image_path   = "${local.project_root}/images/noble-server-cloudimg-amd64.img"
  pool_path    = "${local.project_root}/libvirt-pool"
  ssh_key      = trimspace(file(pathexpand("~/.ssh/id_ed25519.pub")))
  vm_mac       = "52:54:00:12:34:56"
  vm_ip        = "192.168.123.150"
}

resource "libvirt_pool" "lab" {
  name = "netropy-poc"
  type = "dir"

  target = {
    path = local.pool_path
  }
}

resource "libvirt_network" "lab_net" {
  name      = "netropy-poc-net"
  autostart = true

  forward = {
    mode = "nat"
  }

  domain = {
    name = "netropy-poc.local"
  }

  bridge = {
    name = "virbr-netropy"
  }

  ips = [
    {
      address = "192.168.123.1"
      netmask = "255.255.255.0"
      dhcp = {
        ranges = [
          {
            start = "192.168.123.100"
            end   = "192.168.123.200"
          }
        ]
      }
    }
  ]
}

resource "libvirt_volume" "ubuntu_base" {
  name = "ubuntu-noble-base.qcow2"
  pool = libvirt_pool.lab.name

  target = {
    format = {
      type = "qcow2"
    }
  }

  create = {
    content = {
      url = "file://${local.image_path}"
    }
  }
}

resource "libvirt_volume" "ubuntu_disk" {
  name = "netropy-poc-ubuntu.qcow2"
  pool = libvirt_pool.lab.name

  target = {
    format = {
      type = "qcow2"
    }
  }

  capacity = 2147483648

  backing_store = {
    path = libvirt_volume.ubuntu_base.path
    format = {
      type = "qcow2"
    }
  }
}

resource "libvirt_cloudinit_disk" "ubuntu_ci" {
  name = "netropy-poc-cloudinit"

  user_data = templatefile("${path.module}/cloud-init/user-data.yaml", {
    ssh_public_key = local.ssh_key
  })

  meta_data = <<-EOT
    instance-id: netropy-poc-ubuntu
    local-hostname: poc-ubuntu
  EOT

  network_config = <<-EOT
    version: 2
    ethernets:
      nic0:
        match:
          macaddress: "${local.vm_mac}"
        addresses:
          - ${local.vm_ip}/24
        routes:
          - to: default
            via: 192.168.123.1
        nameservers:
          addresses:
            - 192.168.123.1
  EOT
}

resource "libvirt_volume" "ubuntu_cloudinit" {
  name = "netropy-poc-cloudinit.iso"
  pool = libvirt_pool.lab.name

  create = {
    content = {
      url = libvirt_cloudinit_disk.ubuntu_ci.path
    }
  }
}

resource "libvirt_domain" "ubuntu" {
  name   = "netropy-poc-ubuntu"
  memory = 2097152
  vcpu   = 2
  type   = "kvm"

  os = {
    type         = "hvm"
    type_arch    = "x86_64"
    type_machine = "pc"
  }

  features = {
    acpi = true
  }

  devices = {
    disks = [
      {
        source = {
          volume = {
            pool   = libvirt_volume.ubuntu_disk.pool
            volume = libvirt_volume.ubuntu_disk.name
          }
        }
        target = {
          bus = "virtio"
          dev = "vda"
        }
        driver = {
          type = "qcow2"
        }
      },
      {
        device = "cdrom"
        source = {
          volume = {
            pool   = libvirt_volume.ubuntu_cloudinit.pool
            volume = libvirt_volume.ubuntu_cloudinit.name
          }
        }
        target = {
          bus = "sata"
          dev = "sda"
        }
      }
    ]

    interfaces = [
      {
        type  = "network"
        model = { type = "virtio" }
        mac = {
          address = local.vm_mac
        }
        source = {
          network = {
            network = libvirt_network.lab_net.name
          }
        }
      }
    ]

    consoles = [
      {
        type = "pty"
        target = {
          type = "serial"
          port = 0
        }
      }
    ]

    graphics = [
      {
        vnc = {
          auto_port = true
          listen    = "127.0.0.1"
        }
      }
    ]
  }

  running = true
}

data "libvirt_domain_interface_addresses" "ubuntu" {
  domain = libvirt_domain.ubuntu.name
  source = "lease"
}
