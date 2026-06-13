import os

PROJECT_ID = os.environ.get("PROJECT_ID", "")
LOCATION = os.environ.get("LOCATION", "us-central1")  # kept for backwards compat
DOCUMENT_AI_LOCATION = os.environ.get("DOCUMENT_AI_LOCATION", "us")
VERTEX_AI_LOCATION = os.environ.get("VERTEX_AI_LOCATION", "us-central1")
DOCUMENT_AI_PROCESSOR_ID = os.environ.get("DOCUMENT_AI_PROCESSOR_ID", "")
VERTEX_INDEX_ENDPOINT = os.environ.get("VERTEX_INDEX_ENDPOINT", "")
VERTEX_INDEX_ENDPOINT_ID = os.environ.get("VERTEX_INDEX_ENDPOINT_ID", "")
VERTEX_INDEX_ID = os.environ.get("VERTEX_INDEX_ID", "")
VERTEX_INDEX_DEPLOYED_ID = os.environ.get("VERTEX_INDEX_DEPLOYED_ID", "deployed_nem_index")
GCS_BUCKET_NAME = os.environ.get("GCS_BUCKET_NAME", "nem-market-notices-47d6a935")

