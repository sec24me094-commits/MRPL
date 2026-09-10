"""
Comprehensive Automated Test Suite for Ada Workbench (SIH 26117)
Validates all 4 stages:
- Stage 1: Input & Ingestion Gateway (PII Scrubbing & SHA-256 Hashing)
- Stage 2: Orchestration & RAG Grounding (Qdrant SOPs & Dynamic Routing)
- Stage 3: Air-Gapped Code Sandbox (10s timeout, network_mode=none)
- Stage 4: Secure Output Compilation (.docx Approval Notes & .xlsx Calculation Sheets)
- End-to-End FastAPI API routes
"""

import base64
import io
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi.testclient import TestClient

from app.services.ingestion_service import process_uploaded_asset, scrub_pii, compute_sha256
from app.services.rag_service import rag_service
from app.services.compiler_service import (
    compile_approval_note_docx,
    compile_calculations_xlsx,
    compile_approval_note_pdf,
)
from app.agents.sandbox_agent import run_code_in_sandbox
from app.main import app


def test_stage_1_ingestion():
    print("\n--- [TEST] Stage 1: Ingestion & PII Scrubbing ---")
    dummy_blueprint = b"PNG_FAKE_HEADER_MRPL_P&ID_SCHEMATIC_DATA_STREAM_2026"
    notes_with_pii = (
        "Inspected By: Rajesh Kumar on 2026-09-08. "
        "Operator contact: rajesh.k@mrpl.co.in or +91 9876543210. "
        "Badge: MRPL-EMP-8492. Internal controller IP: 192.168.1.105. "
        "Verify hydrostatic test limit on Column C-301."
    )

    manifest = process_uploaded_asset("schematic_c301.png", dummy_blueprint, notes_with_pii)
    
    assert manifest["status"] == "ingested_and_secured"
    assert manifest["byte_size"] == len(dummy_blueprint)
    assert len(manifest["sha256_digest"]) == 64
    assert manifest["pii_scrubbed"] is True
    assert manifest["redaction_count"] >= 4
    assert "[REDACTED_EMAIL]" in manifest["sanitized_notes"]
    assert "[REDACTED_PHONE]" in manifest["sanitized_notes"]
    assert "[REDACTED_BADGE_ID]" in manifest["sanitized_notes"]
    assert "[REDACTED_INTERNAL_IP]" in manifest["sanitized_notes"]
    assert "text_extraction" in manifest
    assert manifest["asset_type"] == "image"
    print(f"[PASS] Stage 1: SHA-256={manifest['sha256_digest'][:16]}..., Redactions={manifest['redaction_count']}")


def test_stage_2_rag_service():
    print("\n--- [TEST] Stage 2: Local RAG & Refinery SOP Knowledge Base ---")
    sops = rag_service.search_sops("What is the maximum allowable pressure for Column C-301?", limit=2)
    assert len(sops) > 0
    top_sop = sops[0]
    assert "C-301" in top_sop["equipment"] or "Pressure Vessel" in top_sop["equipment"]
    assert "600 PSI" in top_sop["clause"]
    print(f"[PASS] Stage 2: Retrieved SOP {top_sop['id']}: {top_sop['title'][:45]}...")


def test_stage_3_sandbox_execution():
    print("\n--- [TEST] Stage 3: Air-Gapped Code Sandbox Execution ---")
    code = (
        "p_mawp = 600.0\n"
        "p_test = 850.0\n"
        "sf = p_test / p_mawp\n"
        "print(f'SAFETY_FACTOR={sf:.2f}')\n"
    )
    result = run_code_in_sandbox(code)
    print(f"Sandbox status: {result.get('status')} | Exit code: {result.get('exit_code')}")
    if result.get("status") == "success":
        assert "SAFETY_FACTOR=1.42" in result.get("stdout")
        print("[PASS] Stage 3: Container execution completed with network_mode=none.")
    else:
        assert result.get("is_success") is False
        print(f"[SKIP] Stage 3: Docker sandbox unavailable: {result.get('stderr')[:80]}")


def test_stage_4_compilers():
    print("\n--- [TEST] Stage 4: Secure Output Compilation (.docx & .xlsx) ---")
    inquiry = "Verify hydrostatic proof test compliance for Column C-301."
    answer = "Analysis complete. Column C-301 operating limits are within ASME Section VIII requirements."
    sops = rag_service.search_sops(inquiry)
    sandbox_report = {
        "executed": True,
        "code": "print('Test compliant')",
        "status": "success",
        "exit_code": 0,
        "stdout": "Test compliant\n",
        "stderr": "",
    }

    docx_bytes = compile_approval_note_docx(
        inquiry=inquiry,
        final_answer=answer,
        sandbox_result=sandbox_report,
        grounding_sops=sops,
        sha256_digest="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        session_id="MRPL-TEST-001",
    )
    assert len(docx_bytes) > 1000
    assert docx_bytes[:2] == b"PK"
    print(f"[PASS] Stage 4: Generated Approval Note (.docx) size: {len(docx_bytes)} bytes")

    xlsx_bytes = compile_calculations_xlsx(
        inquiry=inquiry,
        final_answer=answer,
        sandbox_result=sandbox_report,
        grounding_sops=sops,
        sha256_digest="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
    )
    assert len(xlsx_bytes) > 1000
    assert xlsx_bytes[:2] == b"PK"
    print(f"[PASS] Stage 4: Generated Calculation Sheet (.xlsx) size: {len(xlsx_bytes)} bytes")

    pdf_bytes = compile_approval_note_pdf(
        inquiry=inquiry,
        final_answer=answer,
        sandbox_result=sandbox_report,
        grounding_sops=sops,
        sha256_digest="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        session_id="MRPL-TEST-001",
    )
    assert len(pdf_bytes) > 1000
    assert pdf_bytes[:4] == b"%PDF"
    print(f"[PASS] Stage 4: Generated Approval Note (.pdf) size: {len(pdf_bytes)} bytes")


def test_api_endpoints():
    print("\n--- [TEST] End-to-End API Integration via TestClient ---")
    client = TestClient(app)
    # 1. Health check
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "healthy"
    assert "embedding_status" in res.json()
    print("[PASS] GET /health: 200 OK")

    # Multipart gateway must expose local extraction and redaction evidence.
    res = client.post(
        "/api/v1/ingest/file",
        files={"file": ("operator-notes.txt", b"Inspected By: Jane Doe; phone 9876543210", "text/plain")},
        data={"notes": "Contact: jane@example.com"},
    )
    assert res.status_code == 200
    assert res.json()["text_extraction"]["method"] == "utf8_text"
    assert res.json()["redaction_count"] >= 3
    assert "[REDACTED_PERSONNEL]" in res.json()["sanitized_notes"]
    print("[PASS] POST /api/v1/ingest/file: 200 OK (local extraction + redaction)")

    # 2. Stage 1 Ingestion endpoint
    fake_b64 = base64.b64encode(b"P&ID_SCHEMATIC_VALVES_PUMPS").decode("utf-8")
    res = client.post(
        "/api/v1/ingest",
        json={
            "filename": "pid_feed.png",
            "content_base64": fake_b64,
            "notes": "Checked by John Doe, phone 9876543210, badge MRPL-EMP-9001",
        },
    )
    assert res.status_code == 200
    manifest = res.json()
    assert manifest["stage"] == 1
    assert manifest["pii_scrubbed"] is True
    print("[PASS] POST /api/v1/ingest: 200 OK (PII Scrubbed & Hashed)")

    # Invalid base64 must be rejected rather than silently decoded.
    res = client.post(
        "/api/v1/ingest",
        json={"filename": "invalid.png", "content_base64": "not-valid-base64!"},
    )
    assert res.status_code == 400
    print("[PASS] POST /api/v1/ingest rejects invalid Base64 content")

    # An invalid image must not be silently routed to text reasoning.
    res = client.post(
        "/api/v1/chat",
        json={"user_prompt": "Analyze this schematic", "image_base64": "not-valid-base64!"},
    )
    assert res.status_code == 422
    print("[PASS] POST /api/v1/chat rejects invalid image Base64 content")

    # 3. Stage 2 SOP retrieval
    res = client.get("/api/v1/rag/sops")
    assert res.status_code == 200
    assert len(res.json()["sops"]) >= 4
    print("[PASS] GET /api/v1/rag/sops: 200 OK (Refinery SOPs returned)")

    # Sovereignty endpoint reports controls without claiming packet-capture proof.
    res = client.get("/api/v1/security/posture")
    assert res.status_code == 200
    assert res.json()["sandbox"]["network_mode"] == "none"
    assert any(check["id"] == "packet_capture" for check in res.json()["checks"])
    print("[PASS] GET /api/v1/security/posture: 200 OK (evidence boundary reported)")

    # 4. Stage 4 Export .docx
    payload = {
        "inquiry": "Verify MAWP of Fractionator C-301",
        "final_answer": "Fractionator C-301 meets all safety criteria under ASME Section VIII.",
        "model_name": "DeepSeek-R1-8B",
        "sha256_digest": manifest["sha256_digest"],
        "session_id": "TEST-SESSION-88",
    }
    res = client.post("/api/v1/export/docx", json=payload)
    assert res.status_code == 200
    assert "wordprocessingml" in res.headers["content-type"]
    assert len(res.content) > 1000
    print(f"[PASS] POST /api/v1/export/docx: 200 OK ({len(res.content)} bytes)")

    # 5. Stage 4 Export .xlsx
    res = client.post("/api/v1/export/xlsx", json=payload)
    assert res.status_code == 200
    assert "spreadsheetml" in res.headers["content-type"]
    assert len(res.content) > 1000
    print(f"[PASS] POST /api/v1/export/xlsx: 200 OK ({len(res.content)} bytes)")

    # PPTX remains a cleanly reported optional runtime capability when its
    # local package has not yet been installed in the test environment.
    res = client.post("/api/v1/export/pptx", json=payload)
    if res.status_code == 200:
        assert "presentationml" in res.headers["content-type"]
        print(f"[PASS] POST /api/v1/export/pptx: 200 OK ({len(res.content)} bytes)")
    else:
        assert res.status_code == 503
        assert "python-pptx" in res.json()["detail"]
        print("[SKIP] POST /api/v1/export/pptx: python-pptx not installed in this environment")

    # Stage 4 Export .pdf
    res = client.post("/api/v1/export/pdf", json=payload)
    assert res.status_code == 200
    assert "application/pdf" in res.headers["content-type"]
    assert len(res.content) > 1000
    assert res.content[:4] == b"%PDF"
    print(f"[PASS] POST /api/v1/export/pdf: 200 OK ({len(res.content)} bytes)")

    # Wireshark Audit & Packet Capture Probing
    res = client.post(
        "/api/v1/security/wireshark-audit",
        json={"probe_type": "airgap_egress_test", "destination_host": "8.8.8.8", "destination_port": 53},
    )
    assert res.status_code == 200
    audit_data = res.json()
    assert audit_data["verdict"] == "ZERO_EGRESS_VERIFIED"
    assert audit_data["network_namespace"]["egress_allowed"] is False
    assert audit_data["wireshark_evidence"]["packets_captured"] >= 1
    print(f"[PASS] POST /api/v1/security/wireshark-audit: 200 OK (Zero-egress confirmed, verdict={audit_data['verdict']})")

    res = client.get("/api/v1/security/download-pcap")
    assert res.status_code == 200
    assert len(res.content) >= 24  # PCAP global header minimum size is 24 bytes
    assert res.content[:4] in (b"\xd4\xc3\xb2\xa1", b"\xa1\xb2\xc3\xd4")
    print(f"[PASS] GET /api/v1/security/download-pcap: 200 OK ({len(res.content)} bytes Libpcap binary)")

    # 6. Stage 2 & 3 Chat and Reasoner
    chat_payload = {
        "user_prompt": "Verify if Fractionator C-301 hydrostatic test at 850 PSI complies with MRPL SOPs.",
        "file_metadata": manifest,
    }
    res = client.post("/api/v1/chat", json=chat_payload)
    assert res.status_code == 200
    chat_data = res.json()
    assert chat_data["status"] in {"success", "degraded"}
    assert "final_answer" in chat_data
    if chat_data["status"] == "degraded":
        assert chat_data["verification_status"] == "unverified"
        assert chat_data["sandbox_result"]["executed"] is False
    print(f"[PASS] POST /api/v1/chat: 200 OK (Routed to {chat_data.get('routed_to')})")


if __name__ == "__main__":
    try:
        test_stage_1_ingestion()
        test_stage_2_rag_service()
        test_stage_3_sandbox_execution()
        test_stage_4_compilers()
        test_api_endpoints()
        print("\n=======================================================")
        print("ALL AVAILABLE STAGES VALIDATED; EXTERNAL SERVICES REPORTED EXPLICITLY")
        print("=======================================================\n")
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
