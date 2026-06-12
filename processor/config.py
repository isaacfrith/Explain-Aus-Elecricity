import os

PROJECT_ID = os.environ.get("PROJECT_ID", "")
LOCATION = os.environ.get("LOCATION", "us-central1")  # kept for backwards compat
DOCUMENT_AI_LOCATION = os.environ.get("DOCUMENT_AI_LOCATION", "us")
VERTEX_AI_LOCATION = os.environ.get("VERTEX_AI_LOCATION", "us-central1")
DOCUMENT_AI_PROCESSOR_ID = os.environ.get("DOCUMENT_AI_PROCESSOR_ID", "")
VERTEX_INDEX_ENDPOINT = os.environ.get("VERTEX_INDEX_ENDPOINT", "")
VERTEX_INDEX_ID = os.environ.get("VERTEX_INDEX_ID", "")
