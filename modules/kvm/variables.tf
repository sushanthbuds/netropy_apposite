variable "naming_prefix" {
  type        = string
  description = "Prefix for libvirt resource names"
  default     = "netropy-lab"
}

variable "ssh_public_key" {
  type        = string
  description = "SSH public key injected into Ubuntu instances"
}

variable "ubuntu_image" {
  type        = string
  description = "Path to the Ubuntu cloud image on the KVM host"
}

variable "netropy_image" {
  type        = string
  description = "Path to the Netropy VE OS qcow2 (OVA disk1)"
  default     = ""
}

variable "netropy_config_image" {
  type        = string
  description = "Path to the Netropy VE config qcow2 (OVA disk2, /config)"
  default     = ""
}

variable "subnets" {
  type = object({
    mgmt  = object({ cidr = string })
    data1 = object({ cidr = string })
    data2 = object({ cidr = string })
  })
}

variable "instances" {
  type = object({
    netropy = object({
      mgmt_ip  = string
      data1_ip = string
      data2_ip = string
    })
    linux1 = object({
      mgmt_ip = string
      data_ip = string
    })
    linux2 = object({
      mgmt_ip = string
      data_ip = string
    })
  })
}

variable "options" {
  type = object({
    passthrough_data_ports = optional(bool, false)
    vcpu                   = optional(number, 2)
    memory_mb              = optional(number, 2048)
    provision_netropy      = optional(bool, true)
  })
  default = {
    passthrough_data_ports = false
    vcpu                   = 2
    memory_mb              = 2048
    provision_netropy      = true
  }
}
