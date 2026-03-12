# Outputs for PitWall deployment

output "backend_url" {
  description = "URL of the backend Cloud Run service"
  value       = google_cloud_run_v2_service.backend.uri
}

output "web_url" {
  description = "URL of the web frontend Cloud Run service"
  value       = google_cloud_run_v2_service.web.uri
}

output "redis_host" {
  description = "Redis instance host (internal IP)"
  value       = google_redis_instance.cache.host
}

output "redis_port" {
  description = "Redis instance port"
  value       = google_redis_instance.cache.port
}

output "gcs_bucket" {
  description = "GCS bucket for replay data"
  value       = google_storage_bucket.data.name
}
