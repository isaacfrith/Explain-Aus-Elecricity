# NEM Grid Co-Pilot: Engineering Design Document

## 1. System Overview

The NEM Grid Co-Pilot is an event‑driven RAG (Retrieval‑Augmented Generation) system that ingests Australian Energy Market Operator (AEMO) market notices, extracts text using Document AI, generates embeddings, and stores them in Vertex AI Vector Search. It exposes an intelligent conversational interface capable of executing real‑time analytical queries and contextual root‑cause analysis.

### Key Objectives
- **Zero‑Loss Streaming Ingestion** – Continuously capture AEMO PDF notices.
- **Sub‑Minute Vector Ingest** – Process, embed, and index notices within 60 seconds of upload.
- **Agentic Routing** – Route queries between relational SQL (BigQuery) and vector search.
- **Declarative Infrastructure** – 100% managed with Terraform.

## 2. Architecture Components

The system is divided into three layers:

### 2.1 Ingestion & Streaming
- **Cloud Scheduler** (optional) – Polls AEMO archive periodically.
- **Cloud Run (Ingestor)** – Lightweight Python microservice that:
  - Listens to Eventarc triggers on GCS bucket finalize events.
  - Downloads PDF from GCS.
  - Calls Document AI to extract text.
  - Generates embeddings via Vertex AI `text‑embedding‑004`.
  - Upserts vectors to Vertex AI Vector Search.
- **Eventarc** – Routes GCS object finalised events to Cloud Run.
- **Pub/Sub** (optional) – Decouples ingestion from processing.

### 2.2 Storage & Indexing
- **GCS Bucket** – `nem-market-notices-*` (versioned, 30‑day lifecycle).
- **Vertex AI Vector Search** – ScaNN‑based approximate nearest neighbour index (768 dimensions, DOT_PRODUCT_DISTANCE).
- **Document AI Processor** – `OCR_PROCESSOR` (multi‑region `us`).

### 2.3 Serving & Application
- **Cloud Run** – Hosts the FastAPI application with two endpoints:
  - `POST /` – Eventarc handler (ingestion pipeline).
  - `POST /ask` – Query endpoint (RAG).
- **LangChain** – Orchestrates retrieval and LLM calls (Gemini 1.5 Pro).

## 3. Data Flow

1. AEMO PDF uploaded to GCS bucket → Eventarc trigger.
2. Cloud Run invokes `process_pdf()`:
   - Downloads PDF bytes.
   - Base64‑encodes and sends to Document AI.
   - Receives extracted text.
3. `embed_text()` generates a 768‑dimension vector via `text‑embedding‑004`.
4. `upsert_vector()` writes datapoint to Vertex AI index.
5. User sends query to `/ask` endpoint:
   - Convert query to embedding.
   - Retrieve top‑k similar notices from vector search.
   - Pass retrieved context + question to Gemini.
   - Return answer with source references.

## 4. Infrastructure as Code (Terraform)

All resources are defined in a modular Terraform configuration:


### Key Resources Created
- `google_storage_bucket.market_notices`
- `google_eventarc_trigger.pdf_upload_trigger`
- `google_cloud_run_v2_service.document_processor`
- `google_document_ai_processor.aemo_processor` (location = `us`)
- `google_vertex_ai_index.vector_index` (768 dim, streaming updates)
- `google_vertex_ai_index_endpoint.vector_search_endpoint` (public endpoint for demo)
- Service accounts: `doc-processor-sa`, `eventarc-invoker`
- IAM roles: `documentai.apiUser`, `aiplatform.user`, `storage.objectViewer`, `run.invoker`, `eventarc.eventReceiver`

### State Management
- Remote backend: GCS bucket with versioning and locking.

## 5. Application Code (Cloud Run)

The processor runs inside a Cloud Run container (`document-processor`).  
**Entrypoint:** `main.py` (FastAPI)

### Core Functions
- `process_pdf(gcs_uri)` – Downloads PDF from GCS → base64 → Document AI → returns text.
- `embed_text(text)` – Uses `VertexAIEmbeddings` (model `text‑embedding‑004`).
- `upsert_vector(id, embedding, metadata)` – Calls Vertex AI Matching Engine upsert.
- `eventarc_handler(request)` – Parses CloudEvent, executes the pipeline.

### Environment Variables
| Variable | Value |
|----------|-------|
| `PROJECT_ID` | `gen-lang-client-0220328793` |
| `DOCUMENT_AI_LOCATION` | `us` |
| `DOCUMENT_AI_PROCESSOR_ID` | (from Terraform output) |
| `VERTEX_INDEX_ENDPOINT` | full resource name of the index endpoint |

### Build & Deployment
```bash
cd processor
gcloud builds submit --tag gcr.io/PROJECT_ID/document-processor
gcloud run deploy document-processor \
  --image gcr.io/PROJECT_ID/document-processor \
  --region us-central1 \
  --service-account doc-processor-sa@PROJECT_ID.iam.gserviceaccount.com \
  --set-env-vars "..."