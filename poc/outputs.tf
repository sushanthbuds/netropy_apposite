output "vm_name" {
  description = "Name of the proof-of-concept VM"
  value       = libvirt_domain.ubuntu.name
}

output "vm_ip" {
  description = "Static management IP assigned via cloud-init"
  value       = local.vm_ip
}

output "ssh_command" {
  description = "SSH into the VM as ubuntu"
  value       = "ssh ubuntu@${local.vm_ip}"
}

output "next_steps" {
  description = "Commands to verify the VM after apply"
  value       = <<-EOT
    Wait ~90 seconds for cloud-init, then run:
      ssh ubuntu@${local.vm_ip}
      iperf3 --version
  EOT
}
