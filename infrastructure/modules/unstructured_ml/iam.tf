# IAM for processor runtime SA
resource "google_project_iam_member" "processor_documentai_user" {
  project = var.project_id
  role    = "roles/documentai.apiUser"
  member  = "serviceAccount:${google_service_account.processor_runtime.email}"
}

resource "google_project_iam_member" "processor_storage_object_viewer" {
  project = var.project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.processor_runtime.email}"
}

resource "google_project_iam_member" "processor_storage_object_creator" {
  project = var.project_id
  role    = "roles/storage.objectCreator"
  member  = "serviceAccount:${google_service_account.processor_runtime.email}"
}

resource "google_project_iam_member" "processor_vertex_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.processor_runtime.email}"
}

# Allow the processor to use the embedding model (text-embedding-004)
resource "google_project_iam_member" "processor_embedding_user" {
  project = var.project_id
  role    = "roles/aiplatform.user"
  member  = "serviceAccount:${google_service_account.processor_runtime.email}"
}
