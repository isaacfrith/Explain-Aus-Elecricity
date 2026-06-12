output "gcs_bucket_name" {
  value = module.unstructured_ml.gcs_bucket_name
}

output "document_ai_processor_id" {
  value = module.unstructured_ml.document_ai_processor_id
}

output "vector_search_endpoint" {
  value = module.unstructured_ml.vector_search_index_endpoint
}