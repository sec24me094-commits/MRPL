"""
Stage 2 & Stage 3: Central Agent Orchestrator - Ada Workbench (SIH 26117)
Dynamic Multi-Model Router & Stateful Agent Loop:
- Routes Drawing / Blueprint Analysis -> Qwen2.5-VL-7B (via vision_agent.py)
- Routes Calculation / Compliance Analysis -> DeepSeek-R1-8B (grounded by Qdrant Local RAG node)
- Triggers Stage 3 Sandboxed Docker Execution & Self-Correction Loop for generated code
"""

import base64
import logging
import os
import re
from typing import Any, Dict, List, Optional

import httpx

from app.agents.sandbox_agent import run_code_in_sandbox
from app.agents.vision_agent import parse_schematic_with_qwen
from app.services.rag_service import rag_service

logger = logging.getLogger("ada_workbench.orchestrator")

DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
REASONING_MODEL = os.getenv("OLLAMA_MODEL", "deepseek-r1:8b")
MAX_SELF_CORRECTION_ATTEMPTS = int(os.getenv("MAX_SELF_CORRECTION_ATTEMPTS", "2"))
PYTHON_CODE_REGEX = re.compile(r"```(?:python)?\s*([\s\S]*?)\s*```", re.IGNORECASE)


def extract_python_code(text: str) -> Optional[str]:
    """Scans response text and extracts the first markdown Python block."""
    matches = PYTHON_CODE_REGEX.findall(text)
    if matches:
        return matches[0].strip()
    return None


async def call_deepseek_reasoner(
    http_client: httpx.AsyncClient,
    prompt: str,
    rag_context: Optional[str] = None,
) -> str:
    """
    Submits an engineering prompt to DeepSeek-R1-8B, enriched with authoritative
    MRPL refinery SOP clauses from the local Qdrant RAG store.
    """
    system_instruction = (
        "You are the sovereign AI engineering core of ADA WORKBENCH on MRPL premises. "
        "Your task is to analyze industrial refinery problems, verify compliance against ASME/API codes, "
        "and perform calculations using executable Python code blocks when numerical precision is required.\n"
    )

    if rag_context:
        system_instruction += f"\n[AUTHORITATIVE LOCAL SOP CLAUSES FROM QDRANT VECTOR STORE]:\n{rag_context}\n"

    full_prompt = f"{system_instruction}\nUSER INQUIRY:\n{prompt}\n"

    payload = {
        "model": REASONING_MODEL,
        "prompt": full_prompt,
        "stream": False,
    }

    response = await http_client.post("/api/generate", json=payload)
    response.raise_for_status()
    return response.json().get("response", "")


async def route_and_execute_task(
    user_prompt: str,
    http_client: httpx.AsyncClient,
    image_bytes: Optional[bytes] = None,
    image_base64: Optional[str] = None,
    file_metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Dynamic Central Orchestrator routing workflow:
    1. If image data is present -> Route to Qwen2.5-VL-7B for multimodal schematic analysis.
    2. If text/calculation problem -> Retrieve Qdrant SOP clauses -> Route to DeepSeek-R1-8B.
    3. If executable Python code is produced -> Run in Stage 3 Air-Gapped Sandbox (`network_mode="none"`).
    4. If code execution fails -> Trigger autonomous self-correction re-prompt loop (up to 2 attempts).
    """
    # ── BRANCH A: Visual Blueprint / Schematic Analysis ─────────────────────────
    raw_bytes = image_bytes
    if not raw_bytes and image_base64:
        try:
            # Strip data URI header if present (e.g. data:image/png;base64,...)
            clean_b64 = image_base64.split(",")[-1] if "," in image_base64 else image_base64
            raw_bytes = base64.b64decode(clean_b64)
        except Exception as b64_err:
            logger.warning("Could not decode image_base64: %s", b64_err)

    if raw_bytes and len(raw_bytes) > 0:
        logger.info("Orchestrator Routing -> Vision Model (Qwen2.5-VL-7B) for blueprint analysis")
        vision_result = await parse_schematic_with_qwen(raw_bytes, user_prompt)

        return {
            "status": "success",
            "routed_to": "vision_qwen2.5_vl",
            "model": vision_result.get("model", "qwen2.5-vl:7b"),
            "final_answer": vision_result.get("analysis", ""),
            "code_executed": None,
            "sandbox_result": {"executed": False},
            "self_correction_attempts": 0,
            "correction_history": [],
            "grounding_sops": [],
            "file_attestation": file_metadata,
        }

    # ── BRANCH B: Reasoning & Calculation Core (DeepSeek-R1 + Qdrant RAG) ───────
    logger.info("Orchestrator Routing -> Reasoning Model (DeepSeek-R1-8B) with local RAG grounding")

    # 1. Query Local Qdrant RAG Node for relevant SOPs
    matching_sops = rag_service.search_sops(user_prompt, limit=2)
    rag_context_str = "\n".join([
        f"- {s['id']} [{s['title']}]: {s['clause']}" for s in matching_sops
    ])

    # 2. Call DeepSeek-R1
    current_prompt = user_prompt
    llm_response = await call_deepseek_reasoner(http_client, current_prompt, rag_context=rag_context_str)

    # 3. Check for generated Python script for Stage 3 Sandbox evaluation
    code_block = extract_python_code(llm_response)
    sandbox_result: Dict[str, Any] = {"executed": False}
    correction_history: List[Dict[str, Any]] = []
    attempts = 0

    if code_block:
        logger.info("Detected calculation script in DeepSeek output. Dispatching to Stage 3 air-gapped sandbox...")
        exec_output = run_code_in_sandbox(code_block)
        sandbox_result = {
            "executed": True,
            "code": code_block,
            "status": exec_output.get("status"),
            "exit_code": exec_output.get("exit_code"),
            "stdout": exec_output.get("stdout"),
            "stderr": exec_output.get("stderr"),
            "error_type": exec_output.get("error_type"),
        }

        # 4. Self-Correction Loop on execution / syntax errors
        while not exec_output.get("is_success", False) and attempts < MAX_SELF_CORRECTION_ATTEMPTS:
            attempts += 1
            logger.warning(
                "Sandbox script failed (attempt %d/%d). Initiating autonomous self-correction loop...",
                attempts,
                MAX_SELF_CORRECTION_ATTEMPTS,
            )

            correction_history.append({
                "attempt": attempts,
                "failing_code": code_block,
                "stderr": exec_output.get("stderr"),
                "error_type": exec_output.get("error_type"),
            })

            feedback_prompt = (
                f"Your previous Python calculation script produced an execution error inside our air-gapped sandbox:\n\n"
                f"```python\n{code_block}\n```\n\n"
                f"Traceback / Error Details:\n{exec_output.get('stderr')}\n\n"
                f"Please correct the syntax, variables, or mathematical logic, and return the fixed script inside a ```python ... ``` block."
            )

            llm_response = await call_deepseek_reasoner(http_client, feedback_prompt, rag_context=rag_context_str)
            code_block = extract_python_code(llm_response)
            if not code_block:
                break

            exec_output = run_code_in_sandbox(code_block)
            sandbox_result = {
                "executed": True,
                "code": code_block,
                "status": exec_output.get("status"),
                "exit_code": exec_output.get("exit_code"),
                "stdout": exec_output.get("stdout"),
                "stderr": exec_output.get("stderr"),
                "error_type": exec_output.get("error_type"),
            }

    return {
        "status": "success",
        "routed_to": "reasoning_deepseek_r1",
        "model": REASONING_MODEL,
        "final_answer": llm_response,
        "code_executed": code_block,
        "sandbox_result": sandbox_result,
        "self_correction_attempts": attempts,
        "correction_history": correction_history,
        "grounding_sops": matching_sops,
        "file_attestation": file_metadata,
    }
