import os
import json
import logging
import uuid

import uvicorn
from fastapi import FastAPI, Request, Response
from google.cloud import documentai_v1 as documentai
from google.cloud import storage
from google.cloud.aiplatform import matching_engine
from langchain_google_vertexai import VertexAIEmbeddings

import config

app = FastAPI()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Lazy-initialised singletons — we defer construction to the first request
# so that startup failures (auth, network) don't prevent the port from binding.
# ---------------------------------------------------------------------------
_documentai_client: documentai.DocumentProcessorServiceClient | None = None
_storage_client: storage.Client | None = None
_embedder: VertexAIEmbeddings | None = None
_index_endpoint: matching_engine.MatchingEngineIndexEndpoint | None = None


def get_documentai_client() -> documentai.DocumentProcessorServiceClient:
    global _documentai_client
    if _documentai_client is None:
        _documentai_client = documentai.DocumentProcessorServiceClient()
    return _documentai_client


def get_storage_client() -> storage.Client:
    global _storage_client
    if _storage_client is None:
        _storage_client = storage.Client()
    return _storage_client


def get_embedder() -> VertexAIEmbeddings:
    global _embedder
    if _embedder is None:
        _embedder = VertexAIEmbeddings(
            model_name="text-embedding-004",
            project=config.PROJECT_ID,
        )
    return _embedder


def get_index_endpoint() -> matching_engine.MatchingEngineIndexEndpoint:
    global _index_endpoint
    if _index_endpoint is None:
        _index_endpoint = matching_engine.MatchingEngineIndexEndpoint(
            index_endpoint_name=config.VERTEX_INDEX_ENDPOINT
        )
    return _index_endpoint


# ---------------------------------------------------------------------------
# Business logic
# ---------------------------------------------------------------------------

def process_pdf(gcs_uri: str) -> str:
    """Fetch PDF bytes from GCS and call Document AI to extract text."""
    # Parse gs://bucket/object
    without_scheme = gcs_uri[len("gs://"):]
    bucket_name, _, blob_name = without_scheme.partition("/")

    blob = get_storage_client().bucket(bucket_name).blob(blob_name)
    pdf_bytes = blob.download_as_bytes()

    processor_name = (
        f"projects/{config.PROJECT_ID}"
        f"/locations/{config.DOCUMENT_AI_LOCATION}"
        f"/processors/{config.DOCUMENT_AI_PROCESSOR_ID}"
    )
    raw_document = documentai.RawDocument(
        content=pdf_bytes,
        mime_type="application/pdf",
    )
    doc_request = documentai.ProcessRequest(
        name=processor_name,
        raw_document=raw_document,
    )
    result = get_documentai_client().process_document(request=doc_request)
    return result.document.text


def embed_text(text: str) -> list[float]:
    """Generate embedding using Vertex AI text-embedding-004."""
    return get_embedder().embed_query(text)


def upsert_vector(vector_id: str, embedding: list[float], metadata: dict):
    """Upsert a single datapoint to Vertex AI Vector Search."""
    datapoint = matching_engine.matching_engine_index_endpoint.IndexDatapoint(
        datapoint_id=vector_id,
        feature_vector=embedding,
    )
    get_index_endpoint().upsert_datapoints(datapoints=[datapoint])


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@app.post("/")
async def eventarc_handler(request: Request):
    """Receives Eventarc push events (Cloud Storage object.finalized)."""
    body = await request.json()
    logger.info(f"Received event: {body}")

    # Eventarc delivers GCS events as a CloudEvent whose data mirrors the
    # storage object attributes directly at the top level.
    bucket_name = body.get("bucket") or body.get("bucketId")
    object_name = body.get("name") or body.get("objectId")

    # Fallback: Pub/Sub-style envelope used by some trigger configurations
    if not bucket_name or not object_name:
        message = body.get("message", {})
        attributes = message.get("attributes", {})
        bucket_name = attributes.get("bucketId")
        object_name = attributes.get("objectId")

    if not bucket_name or not object_name:
        logger.error(f"Could not extract bucket/object from event body: {body}")
        return Response(status_code=400, content="Missing bucket or object")

    gcs_uri = f"gs://{bucket_name}/{object_name}"
    logger.info(f"Processing: {gcs_uri}")

    try:
        text = process_pdf(gcs_uri)
        if not text.strip():
            logger.warning(f"No text extracted from {gcs_uri}")
            return Response(status_code=200, content="No text extracted")

        embedding = embed_text(text)

        doc_id = str(uuid.uuid4())
        metadata = {"source": "AEMO", "filename": object_name}
        upsert_vector(doc_id, embedding, metadata)

        logger.info(f"Successfully processed {object_name} -> {doc_id}")
        return Response(status_code=200, content="OK")

    except Exception:
        logger.exception(f"Error processing {gcs_uri}")
        return Response(status_code=500, content="Internal error")


# ---------------------------------------------------------------------------
# Local entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)