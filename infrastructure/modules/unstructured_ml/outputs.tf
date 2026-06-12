output "gcs_bucket_name" {
  value = google_storage_bucket.market_notices.name
}

output "document_ai_processor_id" {
  value = element(split("/", google_document_ai_processor.aemo_processor.name), length(split("/", google_document_ai_processor.aemo_processor.name)) - 1)
}

output "vector_search_index_endpoint" {
  value = google_vertex_ai_index_endpoint.vector_search_endpoint.public_endpoint_domain_name
}

output "cloud_run_service_url" {
  value = google_cloud_run_v2_service.document_processor.uri
}