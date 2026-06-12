import os
import json
import logging
import uuid
import base64


import uvicorn
from fastapi import FastAPI, Request, Response
from google.cloud import storage
from google.cloud import aiplatform_v1
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
_storage_client: storage.Client | None = None
_embedder: VertexAIEmbeddings | None = None
_index_endpoint: matching_engine.MatchingEngineIndexEndpoint | None = None
_index: matching_engine.MatchingEngineIndex | None = None


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


def get_index() -> matching_engine.MatchingEngineIndex:
    global _index
    if _index is None:
        # Require VERTEX_INDEX_ID for upserting
        if not config.VERTEX_INDEX_ID:
            raise ValueError("VERTEX_INDEX_ID is required to upsert vectors.")
        _index = matching_engine.MatchingEngineIndex(
            index_name=config.VERTEX_INDEX_ID,
            project=config.PROJECT_ID,
            location=config.VERTEX_AI_LOCATION
        )
    return _index


# ---------------------------------------------------------------------------
# Business logic
# ---------------------------------------------------------------------------

def process_document(gcs_uri: str) -> str:
    """Download text document directly from GCS (bypassing Document AI)."""
    # Parse gs://bucket/object
    without_scheme = gcs_uri[len("gs://"):]
    bucket_name, _, blob_name = without_scheme.partition("/")
    blob = get_storage_client().bucket(bucket_name).blob(blob_name)
    
    # Download directly as text
    text_content = blob.download_as_text()
    return text_content

def embed_text(text: str) -> list[float]:
    """Generate embedding using Vertex AI text-embedding-004."""
    return get_embedder().embed_query(text)


def upsert_vector(vector_id: str, embedding: list[float], metadata: dict):
    """Upsert a single datapoint to Vertex AI Vector Search."""
    
    # We can store our metadata natively using namespace filtering or protobuf structs.
    # For now, we'll store them as string restrictions so we can filter by them later!
    restricts = []
    for k, v in metadata.items():
        restricts.append(
            aiplatform_v1.IndexDatapoint.Restriction(
                namespace=k,
                allow_list=[str(v)]
            )
        )

    datapoint = aiplatform_v1.IndexDatapoint(
        datapoint_id=vector_id,
        feature_vector=embedding,
        restricts=restricts
    )
    
    # Notice we upsert to the INDEX, not the ENDPOINT
    get_index().upsert_datapoints(datapoints=[datapoint])


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
        text = process_document(gcs_uri)
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