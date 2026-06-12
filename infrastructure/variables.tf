variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region (e.g., us-central1)"
  type        = string
  default     = "us-central1"
}

variable "bucket_name_prefix" {
  description = "Prefix for GCS bucket name (will be globally unique)"
  type        = string
  default     = "nem-market-notices"
}

variable "document_ai_processor_display_name" {
  description = "Display name for Document AI processor"
  type        = string
  default     = "aemo-notice-processor"
}

variable "vector_search_index_name" {
  description = "Name of Vertex AI Vector Search index"
  type        = string
  default     = "nem_notices_index"
}

variable "document_ai_location" {
  description = "Document AI multi-region location (us or eu)"
  type        = string
  default     = "us"
}