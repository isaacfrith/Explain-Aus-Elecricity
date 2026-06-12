variable "project_id" {}
variable "region" {}
variable "bucket_name_prefix" {}
variable "document_ai_processor_display_name" {}
variable "vector_search_index_name" {}

# Document AI only supports multi-region endpoints ("us" or "eu"), not standard GCP regions
variable "document_ai_location" {
  description = "Document AI multi-region location (us or eu)"
  type        = string
  default     = "us"
}