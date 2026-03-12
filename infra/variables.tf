# Terraform variables for PitWall Live deployment

variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "gemini_api_key" {
  description = "Gemini API key for ephemeral token minting"
  type        = string
  sensitive   = true
}

variable "backend_image" {
  description = "Container image for the backend (e.g. gcr.io/PROJECT/pitwall-backend:latest)"
  type        = string
}

variable "web_image" {
  description = "Container image for the web frontend (e.g. gcr.io/PROJECT/pitwall-web:latest)"
  type        = string
}
