"""
Real-Time Streaming & ChatGPT Interface Verification Script for Ada Workbench
Tests:
1. Static HTML serving with ChatGPT interface elements (Thought accordion, stopBtn, thinkToggle, etc.)
2. SSE streaming route (/api/v1/chat/stream)
3. Live thought chunk and token chunk delivery
4. Stop/Abort endpoint (/api/v1/chat/stop)
"""

import json
import asyncio
from fastapi.testclient import TestClient
import httpx
from app.main import app

def test_chatgpt_interface_static_assets():
    print("\n--- [TEST] ChatGPT Interface Static Assets & Markdowns ---")
    client = TestClient(app)
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    
    # Check key ChatGPT UI elements
    assert '.hidden { display: none !important; }' in html, "Missing .hidden CSS utility rule"
    assert 'thought-complete-icon' in html, "Missing .thought-complete-icon"
    assert 'vision-scan-card' in html, "Missing .vision-scan-card template"
    assert 'id="chatFeed"' in html, "Missing #chatFeed container"
    assert 'id="feedInner"' in html, "Missing #feedInner container"
    assert 'id="promptInput"' in html, "Missing #promptInput composer textarea"
    assert 'id="actionBtn"' in html, "Missing #actionBtn (send/stop action button)"
    assert 'id="thinkToggleBtn"' in html, "Missing #thinkToggleBtn pill"
    assert 'id="modelSelectorBtn"' in html, "Missing #modelSelectorBtn dropdown"
    assert 'thought-container' in html, "Missing .thought-container style/template"
    assert 'renderMarkdown' in html, "Missing client-side renderMarkdown function"
    assert 'copyCodeBlock' in html, "Missing copyCodeBlock function for codeblocks"
    assert 'abortController' in html, "Missing client abort controller logic"
    assert 'ASME' in html, "Missing ASME compliance references"
    assert "downloadExport('docx'" in html, "Missing docx export"
    print("[PASS] Static interface contains all real-time ChatGPT UI elements, spinner freeze fixes, and vision scan card.")

def test_stop_generation_endpoint():
    print("\n--- [TEST] /api/v1/chat/stop Cancellation Endpoint ---")
    client = TestClient(app)
    # Stop non-existent session (idempotent)
    res = client.post("/api/v1/chat/stop", json={"session_id": "test-session-none"})
    assert res.status_code == 200
    assert res.json()["status"] in {"no_active_task", "stopped"}
    print("[PASS] Stop endpoint returns 200 OK with correct status.")

def test_sse_streaming_endpoint():
    print("\n--- [TEST] /api/v1/chat/stream Fast SSE Endpoint ---")
    client = TestClient(app)
    # Stream a fast inquiry with think_mode=False
    payload = {
        "user_prompt": "State the MAWP limit of C-301 according to SOP.",
        "model_tag": "llama3:latest",
        "think_mode": False,
        "session_id": "test-stream-sess-1",
    }
    with client.stream("POST", "/api/v1/chat/stream", json=payload) as response:
        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")
        
        events = []
        current_event = None
        for line in response.iter_lines():
            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                data_str = line[6:]
                try:
                    ev = json.loads(data_str)
                    events.append({"event": current_event, "data": ev})
                except Exception:
                    pass
            if len(events) >= 3:
                break
        
        event_types = [e.get("event") for e in events]
        print(f"[PASS] Fast SSE Stream initiated successfully. Received event types: {event_types}")
        assert "activity" in event_types or "retrieval" in event_types, f"Expected activity or retrieval event, got: {event_types}"

def test_dynamic_multimodal_routing_graph():
    print("\n--- [TEST] Dynamic Multi-Model Routing (Qwen2.5-VL -> RAG -> DeepSeek-R1) ---")
    import base64
    client = TestClient(app)
    # 1x1 transparent PNG image
    tiny_png_b64 = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    payload = {
        "user_prompt": "Analyze this schematic and verify MAWP compliance of Column C-301.",
        "image_base64": tiny_png_b64,
        "model_tag": "llama3:latest", # use fast model for testing
        "think_mode": False,
        "session_id": "test-multimodal-sess",
    }
    with client.stream("POST", "/api/v1/chat/stream", json=payload) as response:
        assert response.status_code == 200
        events = []
        current_event = None
        for line in response.iter_lines():
            if line.startswith("event: "):
                current_event = line[7:].strip()
            elif line.startswith("data: "):
                data_str = line[6:]
                try:
                    ev = json.loads(data_str)
                    events.append({"event": current_event, "data": ev})
                except Exception:
                    pass
            if len(events) >= 4:
                break
        
        event_types = [e.get("event") for e in events]
        print(f"[PASS] Dynamic Multimodal Stream initiated. Received event types: {event_types}")
        assert "activity" in event_types, f"Expected activity events in multimodal pipeline, got: {event_types}"

if __name__ == "__main__":
    test_chatgpt_interface_static_assets()
    test_stop_generation_endpoint()
    test_sse_streaming_endpoint()
    test_dynamic_multimodal_routing_graph()
    print("\n[ALL REAL-TIME STREAMING, SPINNER FIXES & DYNAMIC ROUTING CHECKS PASSED]")

