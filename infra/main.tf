# PitWall Live — GCP Infrastructure (Terraform)
# Cloud Run + Memorystore Redis + Firestore + GCS + Secret Manager

terraform {
  required_version = ">= 1.5"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

# ── Enable APIs ────────────────────────────────────────────────────────

resource "google_project_service" "apis" {
  for_each = toset([
    "run.googleapis.com",
    "redis.googleapis.com",
    "firestore.googleapis.com",
    "secretmanager.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudbuild.googleapis.com",
  ])
  service            = each.value
  disable_on_destroy = false
}

# ── Secret Manager — GEMINI_API_KEY ────────────────────────────────────

resource "google_secret_manager_secret" "gemini_key" {
  secret_id = "GEMINI_API_KEY"
  replication {
    auto {}
  }
  depends_on = [google_project_service.apis]
}

resource "google_secret_manager_secret_version" "gemini_key_v1" {
  secret      = google_secret_manager_secret.gemini_key.id
  secret_data = var.gemini_api_key
}

# ── VPC Connector (for Cloud Run → Redis) ──────────────────────────────

resource "google_vpc_access_connector" "connector" {
  name          = "pitwall-vpc"
  region        = var.region
  ip_cidr_range = "10.8.0.0/28"
  network       = "default"
  depends_on    = [google_project_service.apis]
}

# ── Memorystore Redis ──────────────────────────────────────────────────

resource "google_redis_instance" "cache" {
  name           = "pitwall-redis"
  tier           = "BASIC"
  memory_size_gb = 1
  region         = var.region
  redis_version  = "REDIS_7_0"
  depends_on     = [google_project_service.apis]
}

# ── Firestore ──────────────────────────────────────────────────────────

resource "google_firestore_database" "db" {
  project     = var.project_id
  name        = "(default)"
  location_id = var.region
  type        = "FIRESTORE_NATIVE"
  depends_on  = [google_project_service.apis]
}

# ── GCS Bucket (replay NDJSON + demo assets) ───────────────────────────

resource "google_storage_bucket" "data" {
  name     = "${var.project_id}-pitwall-data"
  location = var.region
  uniform_bucket_level_access = true
  force_destroy               = true
}

# ── Cloud Run — Backend ────────────────────────────────────────────────

resource "google_cloud_run_v2_service" "backend" {
  name     = "pitwall-backend"
  location = var.region

  template {
    containers {
      image = var.backend_image
      ports {
        container_port = 8080
      }
      env {
        name  = "REDIS_HOST"
        value = google_redis_instance.cache.host
      }
      env {
        name  = "REDIS_PORT"
        value = tostring(google_redis_instance.cache.port)
      }
      env {
        name  = "ENV"
        value = "production"
      }
      env {
        name = "GEMINI_API_KEY"
        value_source {
          secret_key_ref {
            secret  = google_secret_manager_secret.gemini_key.secret_id
            version = "latest"
          }
        }
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
    vpc_access {
      connector = google_vpc_access_connector.connector.id
      egress    = "PRIVATE_RANGES_ONLY"
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 3
    }
  }

  depends_on = [
    google_project_service.apis,
    google_secret_manager_secret_version.gemini_key_v1,
  ]
}

# Allow unauthenticated access to backend
resource "google_cloud_run_v2_service_iam_member" "backend_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.backend.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}

# ── Cloud Run — Web Frontend ──────────────────────────────────────────

resource "google_cloud_run_v2_service" "web" {
  name     = "pitwall-web"
  location = var.region

  template {
    containers {
      image = var.web_image
      ports {
        container_port = 3000
      }
      env {
        name  = "NEXT_PUBLIC_BACKEND_URL"
        value = google_cloud_run_v2_service.backend.uri
      }
      resources {
        limits = {
          cpu    = "1"
          memory = "512Mi"
        }
      }
    }
    scaling {
      min_instance_count = 0
      max_instance_count = 2
    }
  }

  depends_on = [google_project_service.apis]
}

# Allow unauthenticated access to web
resource "google_cloud_run_v2_service_iam_member" "web_public" {
  project  = var.project_id
  location = var.region
  name     = google_cloud_run_v2_service.web.name
  role     = "roles/run.invoker"
  member   = "allUsers"
}
