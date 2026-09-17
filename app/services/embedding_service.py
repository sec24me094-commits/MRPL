"""Offline BGE embedding adapter.

The adapter only loads a model from a local filesystem path.  It never asks
Hugging Face or another remote registry to download weights at runtime.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ada_workbench.embeddings")

BGE_MODEL_PATH = os.getenv("ADA_BGE_MODEL_PATH", "models/bge-large-en-v1.5")
BGE_MODEL_NAME = os.getenv("ADA_BGE_MODEL_NAME", "BAAI/bge-large-en-v1.5")


class LocalBGEEmbeddingService:
    """Lazy, local-only BGE-large embedding service."""

    def __init__(self, model_path: str = BGE_MODEL_PATH):
        self.model_path = model_path
        self.model_name = BGE_MODEL_NAME
        self.model = None
        self.dimension: Optional[int] = None
        self.error: Optional[str] = None
        self._load_attempted = False

    @property
    def is_available(self) -> bool:
        self._load()
        return self.model is not None

    def _load(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True

        model_dir = Path(self.model_path)
        if not model_dir.is_dir():
            self.error = (
                f"Local BGE model directory does not exist: {model_dir}. "
                "Set ADA_BGE_MODEL_PATH to a provisioned offline model directory."
            )
            return

        try:
            from sentence_transformers import SentenceTransformer

            # Passing a resolved local path makes accidental online resolution
            # impossible for the normal deployment path.
            self.model = SentenceTransformer(str(model_dir), local_files_only=True)
            self.dimension = int(self.model.get_sentence_embedding_dimension())
            logger.info("Loaded local embedding model %s (%d dimensions)", model_dir, self.dimension)
        except TypeError:
            # Older sentence-transformers releases do not expose
            # local_files_only. The path is still local and pre-validated.
            try:
                from sentence_transformers import SentenceTransformer

                self.model = SentenceTransformer(str(model_dir))
                self.dimension = int(self.model.get_sentence_embedding_dimension())
                logger.info("Loaded local embedding model %s (%d dimensions)", model_dir, self.dimension)
            except Exception as exc:
                self.error = f"Could not load local BGE model: {exc}"
        except Exception as exc:
            self.error = f"Could not load local BGE model: {exc}"

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        self._load()
        if self.model is None:
            raise RuntimeError(self.error or "Local BGE embedding model is unavailable.")
        vectors = self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        return [vector.tolist() for vector in vectors]

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]

    def status(self) -> Dict[str, Any]:
        self._load()
        return {
            "available": self.model is not None,
            "model_name": self.model_name,
            "model_path": self.model_path,
            "dimension": self.dimension,
            "offline_only": True,
            "error": self.error,
        }


embedding_service = LocalBGEEmbeddingService()
