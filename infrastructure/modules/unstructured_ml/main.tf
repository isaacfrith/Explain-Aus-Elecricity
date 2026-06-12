# GCS bucket for raw PDFs
resource "google_storage_bucket" "market_notices" {
  name                        = "${var.bucket_name_prefix}-${random_id.bucket_suffix.hex}"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = true  # for dev/demo

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age = 30  # days
    }
    action {
      type = "Delete"
    }
  }
}

resource "random_id" "bucket_suffix" {
  byte_length = 4
}

resource "google_project_iam_member" "eventarc_invoker_receiver" {
  project = var.project_id
  role    = "roles/eventarc.eventReceiver"
  member  = "serviceAccount:${google_service_account.eventarc_invoker.email}"
}

# Eventarc trigger for finalize events on the bucket
resource "google_eventarc_trigger" "pdf_upload_trigger" {
  name     = "pdf-upload-trigger"
  location = var.region
  matching_criteria {
    attribute = "type"
    value     = "google.cloud.storage.object.v1.finalized"
  }
  matching_criteria {
    attribute = "bucket"
    value     = google_storage_bucket.market_notices.name
  }
  destination {
    cloud_run_service {
      service = google_cloud_run_v2_service.document_processor.name
      region  = var.region
    }
  }
  service_account = google_service_account.eventarc_invoker.email

  # IAM bindings must exist before the trigger is created, otherwise the API
  # returns a 403 even though the SA was just created
  depends_on = [
    google_project_iam_member.eventarc_invoker_receiver,
    google_project_iam_member.eventarc_invoker_run,
    google_project_iam_member.gcs_pubsub_publisher,
  ]
}

# Service account for Eventarc to invoke Cloud Run
resource "google_service_account" "eventarc_invoker" {
  account_id   = "eventarc-invoker"
  display_name = "Eventarc Invoker for Cloud Run"
}

resource "google_project_iam_member" "eventarc_invoker_run" {
  project = var.project_id
  role    = "roles/run.invoker"
  member  = "serviceAccount:${google_service_account.eventarc_invoker.email}"
}

# google_storage_project_service_account fetches the GCS-managed service agent
# email AND implicitly provisions it — far more reliable than hand-crafting
# the service-{number}@gs-project-accounts.iam.gserviceaccount.com address.
data "google_storage_project_service_account" "gcs_sa" {
  project = var.project_id
}

resource "google_project_iam_member" "gcs_pubsub_publisher" {
  project = var.project_id
  role    = "roles/pubsub.publisher"
  member  = "serviceAccount:${data.google_storage_project_service_account.gcs_sa.email_address}"
}

data "google_project" "project" {
  project_id = var.project_id
}

# Cloud Run service that will process the PDF (we'll deploy the container separately)
resource "google_cloud_run_v2_service" "document_processor" {
  name     = "document-processor"
  location = var.region
  ingress  = "INGRESS_TRAFFIC_INTERNAL_LOAD_BALANCER" # internal only

  template {
    containers {
      image = "us-docker.pkg.dev/cloudrun/container/hello" # placeholder
      env {
        name  = "DOCUMENT_AI_PROCESSOR_ID"
        value = element(split("/", google_document_ai_processor.aemo_processor.name), length(split("/", google_document_ai_processor.aemo_processor.name)) - 1)
      }
      env {
        name  = "VERTEX_INDEX_ENDPOINT"
        value = google_vertex_ai_index_endpoint.vector_search_endpoint.public_endpoint_domain_name
      }
      env {
        name  = "VERTEX_INDEX_ENDPOINT_ID"
        value = google_vertex_ai_index_endpoint.vector_search_endpoint.id
      }
      env {
        name  = "VERTEX_INDEX_ID"
        value = google_vertex_ai_index.vector_index.id
      }
      env {
        name  = "PROJECT_ID"
        value = var.project_id
      }
    }
    service_account = google_service_account.processor_runtime.email
  }
}

# Service account that the Cloud Run processor will use
resource "google_service_account" "processor_runtime" {
  account_id   = "doc-processor-sa"
  display_name = "Document Processor Runtime SA"
}

# IAM roles for the processor runtime (defined in iam.tf)
# Document AI processor
resource "google_document_ai_processor" "aemo_processor" {
  # Document AI only supports multi-region endpoints: "us" or "eu"
  # It does NOT support standard GCP regions like us-central1
  location     = var.document_ai_location
  display_name = var.document_ai_processor_display_name
  type         = "OCR_PROCESSOR"  # or "FORM_PARSER" if you need forms; OCR_PROCESSOR good for unstructured text
}

# Vertex AI Vector Search resources
resource "google_vertex_ai_index" "vector_index" {
  project   = var.project_id
  region    = var.region
  display_name = var.vector_search_index_name
  description  = "Index for AEMO market notice embeddings"

  metadata {
    contents_delta_uri = "gs://${google_storage_bucket.market_notices.name}/vector-index/"
    config {
      dimensions                  = 768   # text-embedding-004 output dimension
      distance_measure_type       = "DOT_PRODUCT_DISTANCE"
      # Required for tree-AH: how many approximate neighbors to consider during search
      approximate_neighbors_count = 100
      algorithm_config {
        tree_ah_config {
          leaf_node_embedding_count    = 500
          leaf_nodes_to_search_percent = 5
        }
      }
    }
  }

  # streaming updates allowed
  index_update_method = "STREAM_UPDATE"
}

resource "google_vertex_ai_index_endpoint" "vector_search_endpoint" {
  project      = var.project_id
  region       = var.region
  display_name = "${var.vector_search_index_name}-endpoint"

  public_endpoint_enabled = true   # for demo; in prod you'd use private VPC endpoint
}

resource "google_vertex_ai_index_endpoint_deployed_index" "deployed" {
  # Use .id (full resource path) not .name — .name can return just the numeric ID
  # which causes a malformed API URL like /v1/6782238519889756160:deployIndex
  index_endpoint    = google_vertex_ai_index_endpoint.vector_search_endpoint.id
  index             = google_vertex_ai_index.vector_index.id
  deployed_index_id = "deployed_nem_index"
  automatic_resources {
    min_replica_count = 1
    max_replica_count = 1
  }
    depends_on = [
    google_vertex_ai_index.vector_index,
    google_vertex_ai_index_endpoint.vector_search_endpoint
  ]
}

locals {
  document_ai_processor_short_id = element(split("/", google_document_ai_processor.aemo_processor.name), length(split("/", google_document_ai_processor.aemo_processor.name)) - 1)
}