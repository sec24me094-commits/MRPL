"""
Vision Agent Module - Ada Workbench (SIH26117)
Multimodal engineering schematic, P&ID diagram, and technical blueprint parsing
using Qwen2.5-VL:7b running locally via Ollama.
"""

import base64
import logging
import os
from typing import Any, Dict

import httpx

# Configure module logging
logger = logging.getLogger("ada_workbench.vision")

# Ollama Host & Vision Model Configuration
# In Docker containers, host.docker.internal / docker.internal routes to the host machine.
DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434")
VISION_MODEL = os.getenv("OLLAMA_VISION_MODEL", "qwen2.5-vl:7b")
VISION_TIMEOUT_SECONDS = float(os.getenv("OLLAMA_VISION_TIMEOUT", "600.0"))

# Default domain prompt fallback for industrial blueprint analysis
DEFAULT_PROMPT = (
    "You are an expert industrial engineering AI specialized in technical blueprints, "
    "piping and instrumentation diagrams (P&ID), and electrical schematics. "
    "Analyze this image and extract all visible equipment tags, valve IDs, piping lines, "
    "flow directions, and specifications with high precision."
)


async def parse_schematic_with_qwen(image_bytes: bytes, user_query: str) -> Dict[str, Any]:
    """
    Asynchronously submits an engineering schematic or blueprint image to the local
    Ollama instance running qwen2.5-vl:7b.

    Ollama Multimodal Schema:
    POST /api/chat
    {
        "model": "qwen2.5-vl:7b",
        "messages": [
            {
                "role": "user",
                "content": "<analysis_instructions>",
                "images": ["<base64_encoded_image_string>"]
            }
        ],
        "stream": false
    }

    Args:
        image_bytes (bytes): Raw binary bytes of the uploaded schematic image (PNG, JPEG, etc.).
        user_query (str): Engineering prompt/query guiding the extraction focus.

    Returns:
        Dict[str, Any]: Structured dictionary containing:
            {
                "status": "success" | "error",
                "model": str,
                "analysis": str,
                "metadata": Optional[Dict[str, Any]],
                "error": Optional[str]
            }
    """
    if not image_bytes:
        return {
            "status": "error",
            "model": VISION_MODEL,
            "analysis": "",
            "metadata": None,
            "error": "Input image_bytes is empty. Provide a valid schematic image file.",
        }

    # 3. Encode the raw blueprint / P&ID image_bytes into standard base64 string
    base64_image = base64.b64encode(image_bytes).decode("utf-8")

    # Combine domain-specific context with user's specific analysis query
    prompt_content = user_query.strip() if user_query and user_query.strip() else DEFAULT_PROMPT

    # 2. Format payload specifically for qwen2.5-vl:7b under Ollama /api/chat specification
    payload = {
        "model": VISION_MODEL,
        "messages": [
            {
                "role": "user",
                "content": prompt_content,
                "images": [base64_image],
            }
        ],
        "stream": False,
    }

    timeout_config = httpx.Timeout(
        timeout=VISION_TIMEOUT_SECONDS,
        connect=10.0,
        read=VISION_TIMEOUT_SECONDS,
        write=30.0,
    )

    endpoint = f"{DEFAULT_OLLAMA_HOST.rstrip('/')}/api/chat"
    logger.info("Dispatching schematic to %s at %s", VISION_MODEL, endpoint)

    # 1. Use httpx to make asynchronous POST request
    try:
        async with httpx.AsyncClient(timeout=timeout_config) as client:
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()
            data = response.json()

            # 5. Extract structured visual analysis text response
            message_block = data.get("message", {})
            analysis_text = message_block.get("content", "")

            logger.info("Successfully analyzed schematic with %s", VISION_MODEL)
            return {
                "status": "success",
                "model": data.get("model", VISION_MODEL),
                "analysis": analysis_text,
                "metadata": {
                    "total_duration_ns": data.get("total_duration"),
                    "load_duration_ns": data.get("load_duration"),
                    "prompt_eval_count": data.get("prompt_eval_count"),
                    "eval_count": data.get("eval_count"),
                    "done": data.get("done", True),
                },
                "error": None,
            }

    except httpx.ConnectError as conn_err:
        logger.error("Failed to reach Ollama endpoint at %s: %s", DEFAULT_OLLAMA_HOST, conn_err)
        return {
            "status": "error",
            "model": VISION_MODEL,
            "analysis": "",
            "metadata": None,
            "error": (
                f"Could not connect to Ollama host at '{DEFAULT_OLLAMA_HOST}'. "
                "Ensure Ollama is running and has pulled 'qwen2.5-vl:7b'."
            ),
        }

    except httpx.TimeoutException as timeout_err:
        logger.error("Vision inference request timed out: %s", timeout_err)
        return {
            "status": "error",
            "model": VISION_MODEL,
            "analysis": "",
            "metadata": None,
            "error": f"Vision analysis timed out after {VISION_TIMEOUT_SECONDS} seconds.",
        }

    except httpx.HTTPStatusError as http_err:
        logger.error("Ollama vision service responded with HTTP error: %s", http_err)
        return {
            "status": "error",
            "model": VISION_MODEL,
            "analysis": "",
            "metadata": None,
            "error": f"Ollama HTTP {http_err.response.status_code}: {http_err.response.text}",
        }

    except Exception as exc:
        logger.exception("Unexpected exception in parse_schematic_with_qwen: %s", exc)
        return {
            "status": "error",
            "model": VISION_MODEL,
            "analysis": "",
            "metadata": None,
            "error": f"Unexpected vision analysis error: {str(exc)}",
        }
