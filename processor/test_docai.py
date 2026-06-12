import sys
import logging
from main import process_document, embed_text, upsert_vector
import config

# Set up simple logging
logging.basicConfig(level=logging.INFO)

def test_pipeline(gcs_uri: str):
    print(f"--- Starting local test for {gcs_uri} ---")
    
    # 1. Download text directly from GCS
    try:
        print("1. Downloading from GCS...")
        text = process_document(gcs_uri)
        print(f"   Success! Extracted {len(text)} characters.")
        print(f"   Preview: {text[:100]}...\n")
    except Exception as e:
        print(f"   [ERROR] Failed to download text: {e}")
        return

    if not text.strip():
        print("   [WARNING] Text is empty.")
        return

    # 2. Embed text
    try:
        print("2. Generating embedding...")
        embedding = embed_text(text)
        print(f"   Success! Generated embedding of length {len(embedding)}.\n")
    except Exception as e:
        print(f"   [ERROR] Failed to embed text: {e}")
        return

    # 3. Upsert to Vertex Search (Optional for testing, can be commented out)
    try:
        print("3. Upserting to Vector Search...")
        metadata = {"source": "AEMO", "filename": gcs_uri.split("/")[-1]}
        upsert_vector("test-doc-id-1234", embedding, metadata)
        print("   Success! Vector upserted.")
    except Exception as e:
        print(f"   [ERROR] Failed to upsert vector: {e}")
        import traceback
        traceback.print_exc()
        if hasattr(e, "errors"):
            print("Errors:", e.errors)
        if hasattr(e, "details"):
            print("Details:", getattr(e, "details", lambda: e)())
        return

if __name__ == "__main__":
    test_file_uri = "gs://nem-market-notices-47d6a935/NEMITWEB1_MKTNOTICE_20260611.R144238"
    test_pipeline(test_file_uri)
