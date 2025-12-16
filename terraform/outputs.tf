output "instance_id" {
  value = aws_instance.benchmark.id
}

output "public_ip" {
  value = aws_instance.benchmark.public_ip
}

output "ssh" {
  value = "ssh -i ${path.module}/benchmark-key.pem ubuntu@${aws_instance.benchmark.public_ip}"
}
