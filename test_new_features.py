import json
import zipfile
import io
import requests

BASE_URL = "http://localhost:8000"

def test_models_catalog():
    print("\n--- 1. Testing Models Catalog Endpoint ---")
    resp = requests.get(f"{BASE_URL}/api/v1/models/catalog")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert "catalog" in data, "Catalog missing in response"
    assert len(data["catalog"]) > 0, "Catalog should not be empty"
    print(f"Total catalog models: {len(data['catalog'])}")
    engines = {e for m in data["catalog"] for e in m.get("engines", [m.get("engine")])}
    print(f"Supported engines: {engines}")
    assert "ollama" in engines, "Missing Ollama models"
    assert "vllm" in engines, "Missing vLLM models"
    print("Models Catalog test: PASSED")

def test_installed_models():
    print("\n--- 2. Testing Installed Models Endpoint ---")
    resp = requests.get(f"{BASE_URL}/api/v1/models/installed")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert isinstance(data, list)
    print(f"Installed models from Ollama runtime: {data}")
    print("Installed Models test: PASSED")

def test_switch_model():
    print("\n--- 3. Testing Model Switch Endpoint ---")
    resp = requests.post(f"{BASE_URL}/api/v1/models/switch", json={"model_name": "deepseek-r1:8b"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data.get("active_model") == "deepseek-r1:8b"
    print("Model Switch test: PASSED")

def test_chat_stop():
    print("\n--- 4. Testing Chat Stop Endpoint ---")
    resp = requests.post(f"{BASE_URL}/api/v1/chat/stop", json={"session_id": "TEST_SESSION_123"})
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data.get("stopped") is True
    print("Chat Stop test: PASSED")

def test_intranet_rag_ingest():
    print("\n--- 5. Testing Intranet RAG Ingest Endpoint (Zero-Egress) ---")
    payload = {
        "title": "MRPL-SOP-602 FCCU Cyclone Emergency Unblocking",
        "source_url": "http://intranet.mrpl.local/sops/fccu-cyclone.html",
        "equipment_tags": ["FCCU-102", "CYC-201", "VALVE-XV-405"],
        "rbac_token": "MRPL-LEAD-ENG-9001",
        "text_content": (
            "Standard Operating Procedure for Fluid Catalytic Cracking Unit (FCCU). "
            "In case of cyclone dipleg unblocking or pressure differential spike exceeding 14.5 kPa, "
            "immediately initiate secondary steam purge via line 2-ST-402. "
            "Maximum allowable working pressure: 3.5 bar (ASME Section VIII Div 1). "
            "All operators must verify manual bypass valve XV-405 position before clearing."
        )
    }
    resp = requests.post(f"{BASE_URL}/api/v1/rag/ingest", json=payload)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data.get("status") == "SUCCESS_INDEXED"
    assert data.get("chunks_indexed", 0) > 0
    assert "bge-large" in data.get("embedding_model", "")
    assert "mrpl_refinery_sops" in data.get("qdrant_collection", "")
    print(f"Chunks indexed: {data['chunks_indexed']}")
    print(f"SHA-256 Digest: {data.get('sha256_digest')}")
    print(f"Network Scope: {data.get('network_scope')}")
    print("Intranet RAG Ingest test: PASSED")

def test_extension_zip_download():
    print("\n--- 6. Testing Browser Extension Zip Download ---")
    resp = requests.get(f"{BASE_URL}/api/v1/extension/download")
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    assert resp.headers.get("content-type") == "application/zip"
    
    zip_bytes = io.BytesIO(resp.content)
    with zipfile.ZipFile(zip_bytes, "r") as z:
        filenames = z.namelist()
        print(f"Files inside extension zip: {filenames}")
        assert "manifest.json" in filenames, "manifest.json missing in zip"
        assert "popup.html" in filenames, "popup.html missing in zip"
        assert "popup.js" in filenames, "popup.js missing in zip"
        assert "content.js" in filenames, "content.js missing in zip"
        assert "background.js" in filenames, "background.js missing in zip"
    print("Browser Extension Zip Download test: PASSED")

if __name__ == "__main__":
    print("Starting verification of new features...")
    test_models_catalog()
    test_installed_models()
    test_switch_model()
    test_chat_stop()
    test_intranet_rag_ingest()
    test_extension_zip_download()
    print("\n==============================================")
    print("ALL 6 NEW FEATURE TESTS PASSED SUCCESSFULLY!")
    print("==============================================")
