# terraform/main.tf

terraform {
  required_version = ">= 1.7"
  required_providers {
    google = {
      source  = "hashicorp/google"
      version = "~> 5.0"
    }
    google-beta = {
      source  = "hashicorp/google-beta"
      version = "~> 5.0"
    }
  }
}

provider "google" {
  project = var.project_id
  region  = var.region
}

provider "google-beta" {
  project = var.project_id
  region  = var.region
}

# Enable required APIs (many needed for RAG pipeline)
resource "google_project_service" "required" {
  for_each = toset([
    "compute.googleapis.com",          # needed for Vertex Vector Search (runs on Compute Engine)
    "aiplatform.googleapis.com",       # Vertex AI (embedding model + vector search)
    "documentai.googleapis.com",       # Document AI (PDF parsing)
    "storage.googleapis.com",          # GCS
    "eventarc.googleapis.com",         # Eventarc for GCS triggers
    "run.googleapis.com",              # Cloud Run for processor function
    "pubsub.googleapis.com",           # Optional: for async processing
    "cloudbuild.googleapis.com",       # For deploying processor (optional)
  ])
  service            = each.key
  disable_on_destroy = false
}

module "unstructured_ml" {
  source = "./modules/unstructured_ml"
  project_id                     = var.project_id
  region                         = var.region
  bucket_name_prefix             = var.bucket_name_prefix
  document_ai_processor_display_name = var.document_ai_processor_display_name
  vector_search_index_name       = var.vector_search_index_name
  document_ai_location           = var.document_ai_location   
}