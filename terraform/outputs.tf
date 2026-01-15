output "instance_id" {
  value = aws_instance.benchmark.id
}

output "public_ip" {
  value = aws_instance.benchmark.public_ip
}

output "private_key_path" {
  value = local_file.private_key.filename
}

output "ssh" {
  value = "ssh -o IdentitiesOnly=yes -i ${local_file.private_key.filename} ubuntu@${aws_instance.benchmark.public_ip}"
}
