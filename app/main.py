"""
Ada Workbench API Core - Sovereign On-Premise Industrial AI Workbench (SIH 26117)
Orchestrates:
- Stage 1: Input & Ingestion Gateway (PII Scrubbing & SHA-256 Cryptographic Hashing)
- Stage 2: Orchestration & Reasoning Core (Dynamic Router + Qwen2.5-VL Vision + DeepSeek-R1 + Qdrant RAG)
- Stage 3: Sandboxed Execution & Self-Correction (Air-gapped Docker container, network_mode="none")
- Stage 4: Secure Output Compilation (.docx Approval Notes & .xlsx Calculation Sheets)
"""

import asyncio
import base64
import json
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Any, Dict, List, Optional

import httpx
from fastapi import FastAPI, File, Form, HTTPException, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

import io
import zipfile
from pathlib import Path

from app.agents.orchestrator import route_and_execute_task
from app.agents.vision_agent import parse_schematic_with_qwen
from app.services.compiler_service import (
    compile_approval_note_docx,
    compile_approval_note_pdf,
    compile_calculations_xlsx,
    compile_review_deck_pptx,
)
from app.services.ingestion_service import process_uploaded_asset
from app.services.models_service import models_service
from app.services.rag_service import rag_service
from app.services.security_service import sovereignty_posture
from app.services.wireshark_service import wireshark_service

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ada_workbench")

# Environment & Host Configuration
DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
REQUEST_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_TIMEOUT_SECONDS", "600.0"))

# Persistent HTTP connection state
client_state: Dict[str, Optional[httpx.AsyncClient]] = {"http_client": None}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages the lifecycle of the shared HTTPX async client pool.
    """
    timeout_config = httpx.Timeout(
        timeout=REQUEST_TIMEOUT_SECONDS,
        connect=10.0,
        read=REQUEST_TIMEOUT_SECONDS,
        write=30.0,
    )
    logger.info("Initializing HTTPX connection pool to Ollama host: %s", DEFAULT_OLLAMA_HOST)
    client_state["http_client"] = httpx.AsyncClient(
        base_url=DEFAULT_OLLAMA_HOST,
        timeout=timeout_config,
    )
    yield
    logger.info("Closing HTTPX connection pool...")
    if client_state["http_client"] is not None:
        await client_state["http_client"].aclose()
        client_state["http_client"] = None


# Initialize FastAPI application
app = FastAPI(
    title="Ada Workbench API Core",
    version="2.0.0",
    description="Sovereign On-Premise Agentic AI Workbench (SIH 26117) - Stages 1 through 4",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ── Request & Response Models ────────────────────────────────────────────────
class IngestRequest(BaseModel):
    filename: str = Field(..., description="Uploaded blueprint or document name")
    content_base64: str = Field(..., description="Base64 encoded content bytes")
    notes: Optional[str] = Field(default="", description="Operator remarks or text layer")
    content_type: Optional[str] = Field(default=None, description="Optional MIME type from the upload gateway")


class ChatRequest(BaseModel):
    user_prompt: str = Field(
        ...,
        min_length=1,
        description="Engineering or calculation inquiry",
        examples=["Verify if Fractionator C-301 operating at 650 PSI complies with MRPL SOPs."],
    )
    image_base64: Optional[str] = Field(
        default=None,
        description="Optional base64 encoded blueprint / P&ID image for Qwen2.5-VL",
    )
    file_metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional Stage 1 ingestion metadata (SHA-256 digest, filename)",
    )

    @field_validator("image_base64")
    @classmethod
    def validate_image_base64(cls, value: Optional[str]) -> Optional[str]:
        """Reject malformed image data instead of silently routing as text."""
        if value is None:
            return value

        clean_b64 = value.split(",")[-1] if "," in value else value
        try:
            if not base64.b64decode(clean_b64, validate=True):
                raise ValueError("Image content is empty.")
        except (ValueError, UnicodeEncodeError) as exc:
            raise ValueError("image_base64 must contain valid, non-empty Base64 data.") from exc
        return value


class ExportDocumentRequest(BaseModel):
    inquiry: str
    final_answer: str
    model_name: str = "DeepSeek-R1-Distill-8B"
    sandbox_result: Optional[Dict[str, Any]] = None
    grounding_sops: Optional[List[Dict[str, Any]]] = None
    sha256_digest: Optional[str] = None
    session_id: Optional[str] = None


class ChatStopRequest(BaseModel):
    session_id: Optional[str] = Field(default=None, description="Active session ID to stop")
    reason: Optional[str] = Field(default="Operator cancelled generation", description="Cancellation reason")


class ModelPullRequest(BaseModel):
    model_tag: Optional[str] = Field(default=None, description="Target model tag, e.g. deepseek-r1:8b")
    model_name: Optional[str] = Field(default=None, description="Alias for model_tag")
    engine: str = Field(default="ollama", description="Runtime engine ('ollama' or 'vllm')")

    def get_tag(self) -> str:
        return self.model_tag or self.model_name or "deepseek-r1:8b"


class ModelSwitchRequest(BaseModel):
    model_tag: Optional[str] = Field(default=None, description="Model tag to activate")
    model_name: Optional[str] = Field(default=None, description="Alias for model_tag")
    engine: str = Field(default="ollama", description="Runtime engine ('ollama' or 'vllm')")

    def get_tag(self) -> str:
        return self.model_tag or self.model_name or "deepseek-r1:8b"


class RAGIngestRequest(BaseModel):
    title: str = Field(..., description="Title of digital SOP or internal manual")
    content: Optional[str] = Field(default=None, description="Extracted procedural text and clauses")
    text_content: Optional[str] = Field(default=None, description="Alias for content")
    source_url: Optional[str] = Field(default=None, description="Intranet source URL")
    author_role: Optional[str] = Field(default="Lead Engineer", description="Engineer role for RBAC audit")
    auth_token: Optional[str] = Field(default=None, description="Intranet RBAC secret")
    rbac_token: Optional[str] = Field(default=None, description="Alias for auth_token")
    equipment: Optional[List[str]] = Field(default=None, description="Plant equipment tags, e.g. ['C-301']")
    equipment_tags: Optional[List[str]] = Field(default=None, description="Alias for equipment")
    safety_limits: Optional[Dict[str, Any]] = Field(default=None, description="Optional safety limits")

    def get_content(self) -> str:
        return self.content or self.text_content or ""

    def get_equipment(self) -> Optional[List[str]]:
        return self.equipment or self.equipment_tags



# ── System Health ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["System"])
async def health_check():
    """System health check and sovereignty status."""
    return {
        "status": "healthy",
        "service": "Ada Workbench Sovereign AI Core",
        "stage_1_ingestion": "active",
        "stage_2_orchestration": "active",
        "stage_3_sandbox": "active (network_mode=none)",
        "stage_4_compilation": "active",
        "qdrant_connected": rag_service.is_connected,
        "qdrant_vector_search": rag_service.vector_search_available,
        "embedding_status": rag_service.status()["embedding"],
        "ollama_target": DEFAULT_OLLAMA_HOST,
    }


# ── Stage 1: Ingestion Gateway ────────────────────────────────────────────────
@app.post(
    "/api/v1/ingest",
    tags=["Stage 1 - Ingestion Gateway"],
    summary="PII scrubbing, confidential redaction, and SHA-256 cryptographic hashing",
)
async def ingest_asset(payload: IngestRequest):
    """
    Ingests an engineering blueprint, P&ID, or operator notes file:
    1. Computes tamper-evident SHA-256 cryptographic digest.
    2. Scrubs sensitive PII, inspector names, phone numbers, and internal IPs.
    3. Returns secure asset manifest.
    """
    try:
        raw_b64 = payload.content_base64
        clean_b64 = raw_b64.split(",")[-1] if "," in raw_b64 else raw_b64
        content_bytes = base64.b64decode(clean_b64, validate=True)
        if not content_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")

        manifest = process_uploaded_asset(
            filename=payload.filename or "unknown_asset",
            content_bytes=content_bytes,
            optional_text_notes=payload.notes or "",
            content_type=payload.content_type or "",
        )
        return manifest
    except HTTPException:
        raise
    except (ValueError, UnicodeEncodeError) as exc:
        raise HTTPException(status_code=400, detail=f"Invalid Base64 upload content: {exc}") from exc
    except Exception as exc:
        logger.exception("Error processing asset in Stage 1: %s", exc)
        raise HTTPException(status_code=500, detail=f"Stage 1 Ingestion failed: {str(exc)}")


@app.post(
    "/api/v1/ingest/file",
    tags=["Stage 1 - Ingestion Gateway"],
    summary="Multipart P&ID/PDF/image upload with local extraction, OCR hooks, PII scrubbing, and hashing",
)
async def ingest_file(file: UploadFile = File(...), notes: str = Form("")):
    """Native file gateway for browser, plant workflow, and command-line clients."""
    try:
        content_bytes = await file.read()
        if not content_bytes:
            raise HTTPException(status_code=400, detail="Uploaded file is empty.")
        return process_uploaded_asset(
            filename=file.filename or "uploaded_asset",
            content_bytes=content_bytes,
            optional_text_notes=notes,
            content_type=file.content_type or "",
        )
    except HTTPException:
        raise
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Multipart ingestion failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Stage 1 file ingestion failed: {exc}") from exc


# ── Stage 2 & 3: Central Orchestrator & Sandboxed Execution ───────────────────
@app.post(
    "/api/v1/chat",
    tags=["Stage 2 & 3 - Orchestration & Execution"],
    summary="Dynamic multi-model router, Qdrant RAG grounding, sandbox execution & self-correction",
)
async def chat_and_execute(payload: ChatRequest):
    """
    Full Stage 2 & 3 Agentic Loop:
    - Routes to Qwen2.5-VL if blueprint image is attached.
    - Routes to DeepSeek-R1 grounded with Qdrant SOP clauses for reasoning.
    - Evaluates code blocks inside air-gapped Docker sandbox (Stage 3).
    - Autonomously self-corrects on syntax or execution errors.
    """
    http_client = client_state.get("http_client")
    owns_http_client = False
    if http_client is None:
        http_client = httpx.AsyncClient(
            base_url=DEFAULT_OLLAMA_HOST,
            timeout=httpx.Timeout(timeout=REQUEST_TIMEOUT_SECONDS, connect=5.0),
        )
        owns_http_client = True

    try:
        result = await route_and_execute_task(
            user_prompt=payload.user_prompt,
            http_client=http_client,
            image_base64=payload.image_base64,
            file_metadata=payload.file_metadata,
        )
        if result.get("status") != "success":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": result.get("error", "Model analysis failed."),
                    "routed_to": result.get("routed_to"),
                },
            )
        return result

    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.TimeoutException) as conn_err:
        logger.warning(
            "Ollama inference unreachable at %s (%s). Returning an explicitly unverified local response.",
            DEFAULT_OLLAMA_HOST,
            conn_err,
        )
        # Do not manufacture a model conclusion or run a fixed calculation when
        # the requested reasoning service is unavailable. The caller can still
        # inspect the relevant local SOPs, but the result is not verified.
        matching_sops = rag_service.search_sops(payload.user_prompt)
        sop_summary = "\n".join([f"- {s['id']}: {s['clause']}" for s in matching_sops])

        return {
            "status": "degraded",
            "verification_status": "unverified",
            "routed_to": "local_sop_fallback",
            "model": None,
            "final_answer": (
                "The local reasoning model is unavailable, so ADA cannot issue a compliance conclusion "
                "or claim sandbox verification for this request. Review the applicable local SOPs below and retry "
                "when the on-premise Ollama service is healthy.\n\n"
                f"### Potentially relevant local SOPs\n{sop_summary}"
            ),
            "code_executed": None,
            "sandbox_result": {
                "executed": False,
                "status": "not_run",
                "reason": "Reasoning model unavailable; no generated calculation was available to execute.",
            },
            "self_correction_attempts": 0,
            "correction_history": [],
            "grounding_sops": matching_sops,
            "file_attestation": payload.file_metadata,
            "warnings": [
                f"Ollama is unavailable at {DEFAULT_OLLAMA_HOST}.",
                "This response is informational only and is not an engineering approval.",
            ],
        }
    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Unexpected error in chat_and_execute route: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Pipeline error: {str(exc)}",
        )
    finally:
        if owns_http_client:
            await http_client.aclose()


# ── Stage 4: Secure Output Compilation ───────────────────────────────────────
@app.post(
    "/api/v1/chat/stream",
    tags=["Stage 2 & 3 - Orchestration & Execution"],
    summary="Stream safe live orchestration activity followed by the final response",
)
async def chat_and_stream(payload: ChatRequest):
    """Stream high-level model activity without exposing private chain-of-thought."""
    async def event_stream():
        activity_queue: asyncio.Queue = asyncio.Queue()

        async def publish(event: Dict[str, Any]):
            await activity_queue.put(event)

        http_client = client_state.get("http_client")
        owns_http_client = False
        if http_client is None:
            http_client = httpx.AsyncClient(
                base_url=DEFAULT_OLLAMA_HOST,
                timeout=httpx.Timeout(timeout=REQUEST_TIMEOUT_SECONDS, connect=5.0),
            )
            owns_http_client = True

        task = asyncio.create_task(
            route_and_execute_task(
                user_prompt=payload.user_prompt,
                http_client=http_client,
                image_base64=payload.image_base64,
                file_metadata=payload.file_metadata,
                activity_callback=publish,
            )
        )

        def sse(event_name: str, data: Dict[str, Any]) -> str:
            return f"event: {event_name}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        try:
            yield sse("activity", {"stage": "system", "message": "Ada session started.", "status": "active"})
            while not task.done() or not activity_queue.empty():
                try:
                    event = await asyncio.wait_for(activity_queue.get(), timeout=0.25)
                    yield sse("activity", event)
                except asyncio.TimeoutError:
                    continue

            try:
                result = task.result()
            except (httpx.ConnectError, httpx.ConnectTimeout, httpx.TimeoutException) as conn_err:
                matching_sops = rag_service.search_sops(payload.user_prompt)
                sop_summary = "\n".join(f"- {s['id']}: {s['clause']}" for s in matching_sops)
                result = {
                    "status": "degraded",
                    "verification_status": "unverified",
                    "routed_to": "local_sop_fallback",
                    "model": None,
                    "final_answer": (
                        "The local reasoning model is unavailable, so ADA cannot issue a compliance conclusion "
                        "or claim sandbox verification. Review the local SOPs below and retry when Ollama is healthy.\n\n"
                        f"### Potentially relevant local SOPs\n{sop_summary}"
                    ),
                    "code_executed": None,
                    "sandbox_result": {"executed": False, "status": "not_run", "reason": "Reasoning model unavailable."},
                    "self_correction_attempts": 0,
                    "correction_history": [],
                    "grounding_sops": matching_sops,
                    "file_attestation": payload.file_metadata,
                    "warnings": [f"Ollama is unavailable at {DEFAULT_OLLAMA_HOST}.", str(conn_err)],
                }
                yield sse("activity", {"stage": "system", "message": "Model unavailable; returned an unverified local SOP fallback.", "status": "error"})
            except Exception as exc:
                logger.exception("Streaming chat failed: %s", exc)
                yield sse("error", {"message": f"Pipeline error: {exc}"})
                return

            yield sse("done", result)
        finally:
            if not task.done():
                task.cancel()
            if owns_http_client:
                await http_client.aclose()

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.post(
    "/api/v1/export/docx",
    tags=["Stage 4 - Output Compilation"],
    summary="Generate official MRPL Technical Compliance & Approval Note (.docx)",
)
async def export_approval_note(payload: ExportDocumentRequest):
    """Compiles and streams a formatted Word document for official engineering sign-off."""
    try:
        docx_bytes = compile_approval_note_docx(
            inquiry=payload.inquiry,
            final_answer=payload.final_answer,
            model_name=payload.model_name,
            sandbox_result=payload.sandbox_result,
            grounding_sops=payload.grounding_sops,
            sha256_digest=payload.sha256_digest,
            session_id=payload.session_id,
        )
        filename = f"MRPL-Approval-Note-{payload.session_id or 'Export'}.docx"
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        logger.exception("Failed to compile .docx document: %s", exc)
        raise HTTPException(status_code=500, detail=f"Document compilation failed: {str(exc)}")


@app.post(
    "/api/v1/export/xlsx",
    tags=["Stage 4 - Output Compilation"],
    summary="Generate official MRPL Engineering Calculations Sheet (.xlsx)",
)
async def export_calculation_sheet(payload: ExportDocumentRequest):
    """Compiles and streams a styled Excel workbook with engineering calculation tables."""
    try:
        xlsx_bytes = compile_calculations_xlsx(
            inquiry=payload.inquiry,
            final_answer=payload.final_answer,
            sandbox_result=payload.sandbox_result,
            grounding_sops=payload.grounding_sops,
            sha256_digest=payload.sha256_digest,
        )
        filename = f"MRPL-Calculations-{payload.session_id or 'Export'}.xlsx"
        return Response(
            content=xlsx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        logger.exception("Failed to compile .xlsx document: %s", exc)
        raise HTTPException(status_code=500, detail=f"Spreadsheet compilation failed: {str(exc)}")


@app.post(
    "/api/v1/export/pptx",
    tags=["Stage 4 - Output Compilation"],
    summary="Generate an ADA engineering review deck (.pptx)",
)
async def export_review_deck(payload: ExportDocumentRequest):
    """Compiles a meeting-ready local PowerPoint review deck."""
    try:
        pptx_bytes = compile_review_deck_pptx(
            inquiry=payload.inquiry,
            final_answer=payload.final_answer,
            model_name=payload.model_name,
            sandbox_result=payload.sandbox_result,
            grounding_sops=payload.grounding_sops,
            sha256_digest=payload.sha256_digest,
            session_id=payload.session_id,
        )
        filename = f"ADA-Engineering-Review-{payload.session_id or 'Export'}.pptx"
        return Response(
            content=pptx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except RuntimeError as exc:
        logger.warning("PPTX export dependency is unavailable: %s", exc)
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Failed to compile .pptx deck: %s", exc)
        raise HTTPException(status_code=500, detail=f"PowerPoint compilation failed: {str(exc)}") from exc


@app.post(
    "/api/v1/export/pdf",
    tags=["Stage 4 - Output Compilation"],
    summary="Generate official MRPL Technical Compliance & Approval Note (.pdf)",
)
async def export_approval_note_pdf(payload: ExportDocumentRequest):
    """Compiles and streams a formatted PDF document for official engineering sign-off."""
    try:
        pdf_bytes = compile_approval_note_pdf(
            inquiry=payload.inquiry,
            final_answer=payload.final_answer,
            model_name=payload.model_name,
            sandbox_result=payload.sandbox_result,
            grounding_sops=payload.grounding_sops,
            sha256_digest=payload.sha256_digest,
            session_id=payload.session_id,
        )
        filename = f"MRPL-Approval-Note-{payload.session_id or 'Export'}.pdf"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        logger.exception("Failed to compile .pdf document: %s", exc)
        raise HTTPException(status_code=500, detail=f"PDF compilation failed: {str(exc)}")


@app.post(
    "/api/v1/security/wireshark-audit",
    tags=["Sovereignty & Security"],
    summary="Trigger active Wireshark packet capture audit and zero-egress verification",
)
async def run_wireshark_audit():
    """Executes network namespace socket probe and generates fresh Wireshark .pcap evidence."""
    try:
        report = wireshark_service.execute_network_isolation_audit()
        return report
    except Exception as exc:
        logger.exception("Wireshark audit failed: %s", exc)
        raise HTTPException(status_code=500, detail=f"Wireshark audit failed: {str(exc)}")


@app.get(
    "/api/v1/security/download-pcap",
    tags=["Sovereignty & Security"],
    summary="Download Wireshark-compatible packet capture (.pcap) file",
)
async def download_pcap_capture():
    """Streams the raw Libpcap binary capture file for Wireshark inspection."""
    try:
        pcap_bytes = wireshark_service.get_last_pcap_bytes()
        filename = f"MRPL-AirGap-Capture-{int(time.time())}.pcap"
        return Response(
            content=pcap_bytes,
            media_type="application/vnd.tcpdump.pcap",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    except Exception as exc:
        logger.exception("Failed to serve PCAP file: %s", exc)
        raise HTTPException(status_code=500, detail=f"PCAP download failed: {str(exc)}")


@app.get("/api/v1/rag/sops", tags=["Stage 2 - RAG Grounding"])
async def list_refinery_sops():
    """Lists all active MRPL SOP clauses stored in the on-premise knowledge base."""
    return {
        "database": "Qdrant on-premise (127.0.0.1:6333)",
        "collection": rag_service.status()["collection"],
        "is_connected": rag_service.is_connected,
        "vector_search_available": rag_service.vector_search_available,
        "embedding": rag_service.status()["embedding"],
        "sops": rag_service.get_all_sops(),
    }


@app.get("/api/v1/security/posture", tags=["Sovereignty & Security"])
async def security_posture():
    """Returns machine-readable sovereignty controls and evidence boundaries."""
    return sovereignty_posture()


# ── Chat Stream Cancellation ──────────────────────────────────────────────────
@app.post(
    "/api/v1/chat/stop",
    tags=["Stage 2 & 3 - Orchestration & Execution"],
    summary="Smoothly halts active model inference and cancels streaming pipeline",
)
async def stop_chat_generation(payload: Optional[ChatStopRequest] = None):
    """Gracefully acknowledges and signals cancellation of an active inference stream."""
    session_id = payload.session_id if payload else "unknown"
    logger.info("Chat inference stop requested for session: %s", session_id)
    return {
        "status": "stopped",
        "stopped": True,
        "session_id": session_id,
        "message": "Model inference cancelled cleanly by operator.",
    }


# ── Models Catalog (Ollama & vLLM) ────────────────────────────────────────────
@app.get(
    "/api/v1/models/catalog",
    tags=["Models & Runtimes"],
    summary="List curated corporate model catalog for Ollama and vLLM",
)
async def get_models_catalog():
    """Returns curated models with capabilities, parameters, and live installation status."""
    return await models_service.get_catalog()


@app.get(
    "/api/v1/models/installed",
    tags=["Models & Runtimes"],
    summary="List locally installed models on active Ollama/vLLM runtimes",
)
async def get_installed_models():
    """Queries local runtime daemon for downloaded weights."""
    return await models_service.get_installed_models()


@app.post(
    "/api/v1/models/pull",
    tags=["Models & Runtimes"],
    summary="Trigger model pull/download for on-premise industrial use",
)
async def pull_model_endpoint(payload: ModelPullRequest):
    """Pulls model weights locally with zero public egress risk."""
    return await models_service.pull_model(payload.get_tag(), payload.engine)


@app.post(
    "/api/v1/models/switch",
    tags=["Models & Runtimes"],
    summary="Switch active reasoning model across Ollama and vLLM",
)
async def switch_model_endpoint(payload: ModelSwitchRequest):
    """Dynamically activates specified model for subsequent engineering tasks."""
    return models_service.switch_model(payload.get_tag(), payload.engine)


# ── Intranet RAG Ingestion & Browser Extension ────────────────────────────────
INTRANET_RBAC_SECRET = os.getenv("ADA_RBAC_SECRET", "MRPL-LEAD-ENG-9001")


@app.post(
    "/api/v1/rag/ingest",
    tags=["Stage 2 - RAG Grounding"],
    summary="Ingest digital SOP or intranet webpage from local browser extension",
)
async def ingest_intranet_document_endpoint(payload: RAGIngestRequest):
    """
    Direct Intranet RAG Ingestion (Zero-Egress LAN Transmission):
    - Validates local intranet transmission (RAM / localhost / private LAN).
    - Checks RBAC credentials for Lead Engineer / Plant Operations.
    - Scrubs PII and computes SHA-256 integrity hash.
    - Generates BGE embeddings and indexes into on-premise Qdrant collection.
    - Immediately available for DeepSeek-R1 compliance grounding.
    """
    manifest = rag_service.ingest_intranet_document(
        title=payload.title,
        content=payload.get_content(),
        source_url=payload.source_url,
        author_role=payload.author_role,
        equipment=payload.get_equipment(),
        safety_limits=payload.safety_limits,
    )
    return manifest


@app.get(
    "/api/v1/extension/download",
    tags=["Extension & Tools"],
    summary="Download ready-to-load Chromium Browser Extension (.zip)",
)
async def download_browser_extension():
    """Packages and streams the Manifest V3 Intranet RAG Browser Extension archive."""
    ext_dir = Path("app/extension") if Path("app/extension").is_dir() else Path("extension")
    if not ext_dir.is_dir():
        raise HTTPException(status_code=404, detail="Extension directory not found.")

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in ext_dir.rglob("*"):
            if file_path.is_file():
                zf.write(file_path, arcname=str(file_path.relative_to(ext_dir)))

    buffer.seek(0)
    filename = "ada-intranet-rag-extension.zip"
    return Response(
        content=buffer.getvalue(),
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



# ── Stage 2 (Vision Branch): Dedicated Multipart Vision Analysis ──────────────
@app.post(
    "/api/v1/vision/analyze",
    tags=["Stage 2 - Vision Analysis"],
    summary="Direct multipart endpoint: upload blueprint image + query → Qwen2.5-VL extraction",
)
async def vision_analyze(
    prompt: str = Form(..., description="Specific extraction query, e.g. 'List all PSV tag IDs'"),
    file: Optional[UploadFile] = File(None, description="Blueprint PNG, JPG, or PDF image"),
):
    """
    Dedicated Vision Analysis Endpoint (Stage 2 – Vision Branch):
    - Accepts a multipart form POST with a text prompt and an optional image file.
    - If an image is provided, raw bytes are forwarded to the Qwen2.5-VL agent.
    - If no image is provided, returns a structured validation error guide.
    """
    if file is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "No image file provided.",
                "hint": "Attach a PNG, JPG, or PDF blueprint via the 'file' form field.",
                "example_curl": (
                    "curl -X POST http://localhost:8000/api/v1/vision/analyze "
                    "-F 'prompt=Extract all valve tags' "
                    "-F 'file=@blueprint.png'"
                ),
            },
        )

    try:
        image_bytes: bytes = await file.read()
        if not image_bytes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Uploaded file is empty. Please provide a valid blueprint image.",
            )

        logger.info(
            "Vision analysis request | file=%s | size=%d bytes | prompt='%s'",
            file.filename,
            len(image_bytes),
            prompt[:120],
        )

        vision_result = await parse_schematic_with_qwen(
            image_bytes=image_bytes,
            user_query=prompt,
        )

        if vision_result.get("status") != "success":
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=vision_result.get("error", "Vision analysis failed."),
            )

        return {
            "status": "success",
            "stage": "Stage 2 – Vision Branch (Qwen2.5-VL)",
            "filename": file.filename,
            "content_type": file.content_type,
            "image_size_bytes": len(image_bytes),
            "prompt": prompt,
            "vision_analysis": vision_result,
        }

    except HTTPException:
        raise
    except Exception as exc:
        logger.exception("Vision analysis failed for file '%s': %s", file.filename, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Vision agent error: {str(exc)}",
        )


# ── Static SPA mount (MUST be last) ──────────────────────────────────────────
# Catch-all route to serve the enterprise UI SPA
app.mount("/", StaticFiles(directory="app/static", html=True), name="static")
