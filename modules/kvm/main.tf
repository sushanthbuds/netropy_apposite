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
  project_root = abspath("${path.module}/../..")
  pool_path    = "/var/lib/netropy-lab-pool"
  # libvirt provider memory values are in KiB (see poc/: 2097152 = 2 GiB).
  memory_kib = var.options.memory_mb * 1024

  # Linux interface names are limited to 15 characters (IFNAMSIZ).
  subnet_defs = {
    mgmt = {
      name    = "${var.naming_prefix}-mgmt"
      bridge  = "virbr-nl-mgmt"
      cidr    = var.subnets.mgmt.cidr
      gateway = cidrhost(var.subnets.mgmt.cidr, 1)
    }
    data1 = {
      name    = "${var.naming_prefix}-data1"
      bridge  = "virbr-nl-d1"
      cidr    = var.subnets.data1.cidr
      gateway = cidrhost(var.subnets.data1.cidr, 1)
    }
    data2 = {
      name    = "${var.naming_prefix}-data2"
      bridge  = "virbr-nl-d2"
      cidr    = var.subnets.data2.cidr
      gateway = cidrhost(var.subnets.data2.cidr, 1)
    }
  }

  linux1 = {
    name      = "${var.naming_prefix}-linux1"
    hostname  = "linux1"
    mgmt_mac  = "52:54:00:10:00:21"
    data_mac  = "52:54:00:10:01:21"
    mgmt_ip   = var.instances.linux1.mgmt_ip
    data_ip   = var.instances.linux1.data_ip
    mgmt_gw   = local.subnet_defs.mgmt.gateway
    data_gw   = local.subnet_defs.data1.gateway
    mgmt_mask = split("/", var.subnets.mgmt.cidr)[1]
    data_mask = split("/", var.subnets.data1.cidr)[1]
  }

  linux2 = {
    name      = "${var.naming_prefix}-linux2"
    hostname  = "linux2"
    mgmt_mac  = "52:54:00:10:00:22"
    data_mac  = "52:54:00:10:02:22"
    mgmt_ip   = var.instances.linux2.mgmt_ip
    data_ip   = var.instances.linux2.data_ip
    mgmt_gw   = local.subnet_defs.mgmt.gateway
    data_gw   = local.subnet_defs.data2.gateway
    mgmt_mask = split("/", var.subnets.mgmt.cidr)[1]
    data_mask = split("/", var.subnets.data2.cidr)[1]
  }

  netropy = {
    name       = "${var.naming_prefix}-netropy"
    mgmt_mac   = "52:54:00:10:00:10"
    data1_mac  = "52:54:00:10:01:10"
    data2_mac  = "52:54:00:10:02:10"
    mgmt_ip    = var.instances.netropy.mgmt_ip
    data1_ip   = var.instances.netropy.data1_ip
    data2_ip   = var.instances.netropy.data2_ip
  }

  # Static DHCP leases per subnet (more reliable on WSL than cloud-init static IPs).
  dhcp_hosts = {
    mgmt = [
      { mac = local.linux1.mgmt_mac, ip = local.linux1.mgmt_ip, name = "linux1-mgmt" },
      { mac = local.linux2.mgmt_mac, ip = local.linux2.mgmt_ip, name = "linux2-mgmt" },
      { mac = local.netropy.mgmt_mac, ip = local.netropy.mgmt_ip, name = "netropy-mgmt" },
    ]
    data1 = [
      { mac = local.linux1.data_mac, ip = local.linux1.data_ip, name = "linux1-data" },
      { mac = local.netropy.data1_mac, ip = local.netropy.data1_ip, name = "netropy-data1" },
    ]
    data2 = [
      { mac = local.linux2.data_mac, ip = local.linux2.data_ip, name = "linux2-data" },
      { mac = local.netropy.data2_mac, ip = local.netropy.data2_ip, name = "netropy-data2" },
    ]
  }
}

resource "libvirt_pool" "lab" {
  name = var.naming_prefix
  type = "dir"

  target = {
    path = local.pool_path
  }
}

resource "libvirt_network" "subnets" {
  for_each  = local.subnet_defs
  name      = each.value.name
  autostart = true

  forward = {
    mode = "nat"
  }

  domain = {
    name = "${each.key}.${var.naming_prefix}.local"
  }

  bridge = {
    name = each.value.bridge
  }

  ips = [
    {
      address = each.value.gateway
      netmask = cidrnetmask(each.value.cidr)
      dhcp = {
        hosts = local.dhcp_hosts[each.key]
        ranges = [
          {
            start = cidrhost(each.value.cidr, 100)
            end   = cidrhost(each.value.cidr, 200)
          }
        ]
      }
    }
  ]
}

resource "libvirt_volume" "linux_disks" {
  for_each = {
    linux1 = local.linux1.name
    linux2 = local.linux2.name
  }

  name = "${each.value}.qcow2"
  pool = libvirt_pool.lab.name

  target = {
    format = {
      type = "qcow2"
    }
  }

  capacity = 4294967296

  create = {
    content = {
      url = "file://${var.ubuntu_image}"
    }
  }
}

resource "libvirt_cloudinit_disk" "linux1_ci" {
  name = "${local.linux1.name}-cloudinit"

  user_data = templatefile("${path.module}/cloud-init/linux-user-data.yaml", {
    hostname       = local.linux1.hostname
    ssh_public_key = var.ssh_public_key
  })

  network_config = templatefile("${path.module}/cloud-init/linux-network-config.yaml", {
    mgmt_mac = local.linux1.mgmt_mac
    data_mac = local.linux1.data_mac
  })

  meta_data = <<-EOT
    instance-id: ${local.linux1.name}
    local-hostname: ${local.linux1.hostname}
  EOT
}

resource "libvirt_cloudinit_disk" "linux2_ci" {
  name = "${local.linux2.name}-cloudinit"

  user_data = templatefile("${path.module}/cloud-init/linux-user-data.yaml", {
    hostname       = local.linux2.hostname
    ssh_public_key = var.ssh_public_key
  })

  network_config = templatefile("${path.module}/cloud-init/linux-network-config.yaml", {
    mgmt_mac = local.linux2.mgmt_mac
    data_mac = local.linux2.data_mac
  })

  meta_data = <<-EOT
    instance-id: ${local.linux2.name}
    local-hostname: ${local.linux2.hostname}
  EOT
}

resource "libvirt_volume" "linux_cloudinit" {
  for_each = {
    linux1 = libvirt_cloudinit_disk.linux1_ci.path
    linux2 = libvirt_cloudinit_disk.linux2_ci.path
  }

  name = "${var.naming_prefix}-${each.key}-cloudinit.iso"
  pool = libvirt_pool.lab.name

  create = {
    content = {
      url = each.value
    }
  }
}

resource "libvirt_domain" "linux1" {
  name       = local.linux1.name
  memory     = local.memory_kib
  vcpu       = var.options.vcpu
  type       = "kvm"
  autostart  = true

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
            pool   = libvirt_volume.linux_disks["linux1"].pool
            volume = libvirt_volume.linux_disks["linux1"].name
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
            pool   = libvirt_volume.linux_cloudinit["linux1"].pool
            volume = libvirt_volume.linux_cloudinit["linux1"].name
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
          address = local.linux1.mgmt_mac
        }
        source = {
          network = {
            network = libvirt_network.subnets["mgmt"].name
          }
        }
      },
      {
        type  = "network"
        model = { type = "virtio" }
        mac = {
          address = local.linux1.data_mac
        }
        source = {
          network = {
            network = libvirt_network.subnets["data1"].name
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

resource "libvirt_domain" "linux2" {
  name       = local.linux2.name
  memory     = local.memory_kib
  vcpu       = var.options.vcpu
  type       = "kvm"
  autostart  = true

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
            pool   = libvirt_volume.linux_disks["linux2"].pool
            volume = libvirt_volume.linux_disks["linux2"].name
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
            pool   = libvirt_volume.linux_cloudinit["linux2"].pool
            volume = libvirt_volume.linux_cloudinit["linux2"].name
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
          address = local.linux2.mgmt_mac
        }
        source = {
          network = {
            network = libvirt_network.subnets["mgmt"].name
          }
        }
      },
      {
        type  = "network"
        model = { type = "virtio" }
        mac = {
          address = local.linux2.data_mac
        }
        source = {
          network = {
            network = libvirt_network.subnets["data2"].name
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

# Netropy VE VM — enable when image is available (options.provision_netropy = true)
resource "libvirt_volume" "netropy_disk" {
  count = var.options.provision_netropy ? 1 : 0
  name  = "${local.netropy.name}.qcow2"
  pool  = libvirt_pool.lab.name

  target = {
    format = {
      type = "qcow2"
    }
  }

  capacity = 4294967296

  create = {
    content = {
      url = "file://${var.netropy_image}"
    }
  }
}

resource "libvirt_domain" "netropy" {
  count      = var.options.provision_netropy ? 1 : 0
  name       = local.netropy.name
  memory     = 4194304
  vcpu       = 2
  type       = "kvm"
  autostart  = true

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
            pool   = libvirt_volume.netropy_disk[0].pool
            volume = libvirt_volume.netropy_disk[0].name
          }
        }
        target = {
          bus = "virtio"
          dev = "vda"
        }
        driver = {
          type = "qcow2"
        }
      }
    ]

    interfaces = [
      {
        type  = "network"
        model = { type = "virtio" }
        mac = {
          address = local.netropy.mgmt_mac
        }
        source = {
          network = {
            network = libvirt_network.subnets["mgmt"].name
          }
        }
      },
      {
        type  = "network"
        model = { type = "virtio" }
        mac = {
          address = local.netropy.data1_mac
        }
        source = {
          network = {
            network = libvirt_network.subnets["data1"].name
          }
        }
      },
      {
        type  = "network"
        model = { type = "virtio" }
        mac = {
          address = local.netropy.data2_mac
        }
        source = {
          network = {
            network = libvirt_network.subnets["data2"].name
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
