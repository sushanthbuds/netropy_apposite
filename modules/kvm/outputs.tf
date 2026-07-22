output "linux1_mgmt_ip" {
  value = var.instances.linux1.mgmt_ip
}

output "linux1_data_ip" {
  value = var.instances.linux1.data_ip
}

output "linux2_mgmt_ip" {
  value = var.instances.linux2.mgmt_ip
}

output "linux2_data_ip" {
  value = var.instances.linux2.data_ip
}

output "netropy_provisioned" {
  value = var.options.provision_netropy
}

output "netropy_mgmt_ip" {
  value = var.options.provision_netropy ? var.instances.netropy.mgmt_ip : null
}

output "ssh_linux1" {
  value = "ssh ubuntu@${var.instances.linux1.mgmt_ip}"
}

output "ssh_linux2" {
  value = "ssh ubuntu@${var.instances.linux2.mgmt_ip}"
}

output "iperf3_example" {
  value = "iperf3 -c ${var.instances.linux2.data_ip} -B ${var.instances.linux1.data_ip}"
}

output "next_steps" {
  value = <<-EOT
    Wait ~90 seconds for cloud-init on both Linux VMs, then:
      ssh ubuntu@${var.instances.linux1.mgmt_ip}
      ssh ubuntu@${var.instances.linux2.mgmt_ip}
      iperf3 --version
    Configure Netropy via its management UI, then run:
      iperf3 -c ${var.instances.linux2.data_ip} -B ${var.instances.linux1.data_ip}
  EOT
}
