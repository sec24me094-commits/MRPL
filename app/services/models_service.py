"""
Models Service for Ada Workbench (SIH 26117)
Provides corporate model catalog management, status inspection, dynamic switching,
and pull handling strictly across on-premise Ollama and vLLM runtimes.
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger("ada_workbench.models")

DEFAULT_OLLAMA_HOST = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
DEFAULT_VLLM_HOST = os.getenv("VLLM_BASE_URL", "http://localhost:8000")

# Enterprise Industrial Model Catalog (Ollama & vLLM)
ENTERPRISE_MODELS_CATALOG: List[Dict[str, Any]] = [
    {
        "id": "deepseek-r1:8b",
        "name": "DeepSeek-R1 (8B)",
        "tag": "deepseek-r1:8b",
        "engines": ["ollama", "vllm"],
        "default_engine": "ollama",
        "parameter_size": "8.2B",
        "quantization": "Q4_K_M",
        "context_length": "131,072 tokens",
        "download_size": "4.9 GB",
        "description": "Primary sovereign reasoning model. Performs ASME Section VIII formula verification, step-by-step mathematical reasoning, and Python sandbox generation.",
        "capabilities": ["Reasoning", "Math / Physics", "Sandbox Code"],
        "recommended": True,
        "is_active": True,
    },
    {
        "id": "deepseek-r1:14b",
        "name": "DeepSeek-R1 (14B High-Precision)",
        "tag": "deepseek-r1:14b",
        "engines": ["ollama", "vllm"],
        "default_engine": "ollama",
        "parameter_size": "14.8B",
        "quantization": "Q4_K_M",
        "context_length": "131,072 tokens",
        "download_size": "9.0 GB",
        "description": "High-precision enterprise reasoning model for complex multi-stage thermal and pressure vessel safety derivations.",
        "capabilities": ["High Precision Reasoning", "Complex Derivations"],
        "recommended": False,
        "is_active": False,
    },
    {
        "id": "qwen2.5vl:7b",
        "name": "Qwen2.5-VL (7B Industrial Vision)",
        "tag": "qwen2.5vl:7b",
        "engines": ["ollama", "vllm"],
        "default_engine": "ollama",
        "parameter_size": "8.3B",
        "quantization": "Q4_K_M",
        "context_length": "128,000 tokens",
        "download_size": "5.6 GB",
        "description": "Sovereign multimodal model for P&ID blueprints, line diagrams, instrumentation symbols, and scanned refinery drawings.",
        "capabilities": ["P&ID Vision", "Schematic OCR", "Equipment Tagging"],
        "recommended": True,
        "is_active": False,
    },
    {
        "id": "llama3:8b",
        "name": "Meta Llama 3 (8B)",
        "tag": "llama3:latest",
        "engines": ["ollama", "vllm"],
        "default_engine": "ollama",
        "parameter_size": "8.0B",
        "quantization": "Q4_0",
        "context_length": "8,192 tokens",
        "download_size": "4.3 GB",
        "description": "High-throughput procedural model for rapid SOP clause extraction and conversational operations.",
        "capabilities": ["Conversational Assistant", "Fast Summaries"],
        "recommended": False,
        "is_active": False,
    },
    {
        "id": "mistral:7b",
        "name": "Mistral Instruct (7B)",
        "tag": "mistral:7b",
        "engines": ["ollama", "vllm"],
        "default_engine": "ollama",
        "parameter_size": "7.2B",
        "quantization": "Q4_0",
        "context_length": "32,768 tokens",
        "download_size": "4.1 GB",
        "description": "Deterministic instruction-following model for strict operating limits and compliance checklist audits.",
        "capabilities": ["Instruction Following", "Operating Limits"],
        "recommended": False,
        "is_active": False,
    },
    {
        "id": "codellama:7b",
        "name": "Code Llama (7B)",
        "tag": "codellama:7b",
        "engines": ["ollama"],
        "default_engine": "ollama",
        "parameter_size": "6.9B",
        "quantization": "Q4_0",
        "context_length": "16,384 tokens",
        "download_size": "3.8 GB",
        "description": "Specialized Python generation model for air-gapped numerical calculations and NumPy/SciPy sandbox scripts.",
        "capabilities": ["Python Calculation", "Sandbox Optimization"],
        "recommended": False,
        "is_active": False,
    },
]


class ModelsService:
    def __init__(self, ollama_url: str = DEFAULT_OLLAMA_HOST, vllm_url: str = DEFAULT_VLLM_HOST):
        self.ollama_url = ollama_url.rstrip("/")
        self.vllm_url = vllm_url.rstrip("/")
        self.active_reasoning_model = os.getenv("OLLAMA_MODEL", "deepseek-r1:8b")
        self.active_engine = "ollama"
        self._pulling_tasks: Dict[str, Dict[str, Any]] = {}

    async def get_installed_models(self) -> List[Dict[str, Any]]:
        """Queries local Ollama instance for installed models."""
        installed: List[Dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.ollama_url}/api/tags")
                if res.status_code == 200:
                    data = res.json()
                    for m in data.get("models", []):
                        installed.append({
                            "name": m.get("name"),
                            "model": m.get("model"),
                            "size_bytes": m.get("size", 0),
                            "modified_at": m.get("modified_at"),
                            "engine": "ollama",
                            "capabilities": m.get("capabilities", []),
                            "parameter_size": m.get("details", {}).get("parameter_size", "Unknown"),
                        })
        except Exception as exc:
            logger.warning("Could not reach Ollama at %s to list models: %s", self.ollama_url, exc)
        return installed

    async def get_catalog(self) -> Dict[str, Any]:
        """Returns the complete catalog with live installation status from local runtimes."""
        installed = await self.get_installed_models()
        installed_names = {m["name"] for m in installed}
        installed_tags = {m["model"] for m in installed}

        catalog = []
        for item in ENTERPRISE_MODELS_CATALOG:
            is_installed = item["tag"] in installed_names or item["tag"] in installed_tags
            pull_state = self._pulling_tasks.get(item["tag"])
            catalog.append({
                **item,
                "engine": item.get("default_engine", "ollama"),
                "installed": is_installed,
                "is_installed": is_installed,
                "company_purpose": item.get("description", ""),
                "is_active": item["tag"] == self.active_reasoning_model,
                "pull_status": pull_state.get("status") if pull_state else ("installed" if is_installed else "available"),
                "pull_progress": pull_state.get("progress", 0) if pull_state else (100 if is_installed else 0),
            })

        return {
            "active_reasoning_model": self.active_reasoning_model,
            "active_engine": self.active_engine,
            "ollama_host": self.ollama_url,
            "vllm_host": self.vllm_url,
            "catalog": catalog,
            "installed_count": len(installed),
        }

    async def pull_model(self, model_tag: str, engine: str = "ollama") -> Dict[str, Any]:
        """Initiates a model download/pull task on the selected engine."""
        if engine.lower() != "ollama":
            return {
                "status": "configured",
                "message": f"vLLM model target '{model_tag}' registered in runtime configuration.",
                "model_tag": model_tag,
                "engine": "vllm",
            }

        if model_tag in self._pulling_tasks and self._pulling_tasks[model_tag].get("status") == "pulling":
            return {"status": "pulling", "message": f"Model '{model_tag}' is already downloading."}

        self._pulling_tasks[model_tag] = {"status": "pulling", "progress": 5, "message": "Initiating pull..."}
        asyncio.create_task(self._execute_ollama_pull(model_tag))

        return {
            "status": "started",
            "model_tag": model_tag,
            "engine": "ollama",
            "message": f"Started pulling model '{model_tag}' via sovereign on-premise Ollama daemon.",
        }

    async def _execute_ollama_pull(self, model_tag: str):
        try:
            logger.info("Executing Ollama pull for '%s'...", model_tag)
            async with httpx.AsyncClient(timeout=1800.0) as client:
                res = await client.post(
                    f"{self.ollama_url}/api/pull",
                    json={"name": model_tag, "stream": False},
                )
                if res.status_code == 200:
                    self._pulling_tasks[model_tag] = {"status": "completed", "progress": 100, "message": "Model ready"}
                    logger.info("Model '%s' successfully pulled.", model_tag)
                else:
                    self._pulling_tasks[model_tag] = {"status": "error", "progress": 0, "message": f"Pull failed: {res.text}"}
        except Exception as exc:
            logger.exception("Failed pulling model '%s': %s", model_tag, exc)
            self._pulling_tasks[model_tag] = {"status": "error", "progress": 0, "message": str(exc)}

    def switch_model(self, model_tag: str, engine: str = "ollama") -> Dict[str, Any]:
        """Switches the active reasoning model."""
        self.active_reasoning_model = model_tag
        self.active_engine = engine
        os.environ["OLLAMA_MODEL"] = model_tag
        logger.info("Switched active reasoning model to '%s' on %s", model_tag, engine)
        return {
            "status": "success",
            "active_model": model_tag,
            "active_engine": engine,
            "message": f"Active sovereign reasoning model switched to {model_tag} ({engine}).",
        }


models_service = ModelsService()
