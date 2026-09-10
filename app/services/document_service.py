"""Local document inspection and text extraction for the Stage 1 gateway.

The service is deliberately offline-first.  It never uploads an asset and it
does not silently fall back to an online OCR provider.  Optional PDF/OCR
libraries are loaded lazily so the API can still accept binary assets when a
particular extractor is not installed on the sovereign host.
"""

from __future__ import annotations

import io
import logging
import mimetypes
import os
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger("ada_workbench.documents")

MAX_ASSET_BYTES = int(os.getenv("ADA_MAX_ASSET_BYTES", str(50 * 1024 * 1024)))

SUPPORTED_EXTENSIONS = {
    ".pdf": "pdf",
    ".png": "image",
    ".jpg": "image",
    ".jpeg": "image",
    ".webp": "image",
    ".bmp": "image",
    ".txt": "text",
    ".md": "text",
    ".csv": "text",
}


def classify_asset(filename: str, content_type: Optional[str] = None) -> str:
    """Return a conservative asset class without trusting the filename alone."""
    suffix = Path(filename or "").suffix.lower()
    if suffix in SUPPORTED_EXTENSIONS:
        return SUPPORTED_EXTENSIONS[suffix]
    if content_type:
        if content_type == "application/pdf":
            return "pdf"
        if content_type.startswith("image/"):
            return "image"
        if content_type.startswith("text/"):
            return "text"
    return "binary"


def validate_asset(filename: str, content_bytes: bytes, content_type: Optional[str] = None) -> Dict[str, Any]:
    """Validate size and report the local type classification."""
    if not content_bytes:
        raise ValueError("Uploaded file is empty.")
    if len(content_bytes) > MAX_ASSET_BYTES:
        raise ValueError(
            f"Uploaded file exceeds the local limit of {MAX_ASSET_BYTES} bytes."
        )

    asset_type = classify_asset(filename, content_type)
    warnings = []
    if asset_type == "binary":
        warnings.append("File type is not recognized; binary provenance is preserved but text extraction was skipped.")
    return {
        "asset_type": asset_type,
        "content_type": content_type or mimetypes.guess_type(filename or "")[0],
        "extension": Path(filename or "").suffix.lower(),
        "warnings": warnings,
    }


def _extract_pdf_text(content_bytes: bytes) -> Dict[str, Any]:
    try:
        from pypdf import PdfReader
    except ImportError:
        return {
            "text": "",
            "method": "unavailable",
            "page_count": None,
            "warnings": ["pypdf is not installed; PDF text extraction was not available."],
        }

    try:
        reader = PdfReader(io.BytesIO(content_bytes))
        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")
        text = "\n\n".join(part.strip() for part in pages if part.strip())
        if text:
            return {
                "text": text,
                "method": "pypdf_text_layer",
                "page_count": len(reader.pages),
                "warnings": [],
            }

        # OCR is optional because a sovereign deployment must install and
        # validate its local rasterizer/Tesseract binary explicitly.
        try:
            from pdf2image import convert_from_bytes
            import pytesseract

            images = convert_from_bytes(content_bytes, dpi=200)
            ocr_text = "\n\n".join(pytesseract.image_to_string(image) for image in images).strip()
            return {
                "text": ocr_text,
                "method": "pdf_ocr" if ocr_text else "pdf_ocr_empty",
                "page_count": len(reader.pages),
                "warnings": [] if ocr_text else ["PDF has no text layer and local OCR returned no text."],
            }
        except ImportError:
            return {
                "text": "",
                "method": "scanned_pdf_unavailable",
                "page_count": len(reader.pages),
                "warnings": [
                    "PDF has no text layer. Install the local pdf2image, pytesseract, and Tesseract runtime for OCR."
                ],
            }
        except Exception as exc:
            logger.warning("Local PDF OCR failed: %s", exc)
            return {
                "text": "",
                "method": "scanned_pdf_failed",
                "page_count": len(reader.pages),
                "warnings": [f"Local PDF OCR failed: {exc}"],
            }
    except Exception as exc:
        return {
            "text": "",
            "method": "pdf_error",
            "page_count": None,
            "warnings": [f"PDF parsing failed: {exc}"],
        }


def _extract_image_text(content_bytes: bytes) -> Dict[str, Any]:
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return {
            "text": "",
            "method": "ocr_unavailable",
            "page_count": None,
            "warnings": ["Install pytesseract and the local Tesseract runtime for image OCR."],
        }

    try:
        text = pytesseract.image_to_string(Image.open(io.BytesIO(content_bytes))).strip()
        return {
            "text": text,
            "method": "image_ocr" if text else "image_ocr_empty",
            "page_count": 1,
            "warnings": [] if text else ["Local image OCR returned no text."],
        }
    except Exception as exc:
        logger.warning("Local image OCR failed: %s", exc)
        return {
            "text": "",
            "method": "image_ocr_failed",
            "page_count": 1,
            "warnings": [f"Local image OCR failed: {exc}"],
        }


def extract_local_text(
    filename: str,
    content_bytes: bytes,
    content_type: Optional[str] = None,
) -> Dict[str, Any]:
    """Extract text using only installed local parsers and OCR tooling."""
    asset_info = validate_asset(filename, content_bytes, content_type)
    asset_type = asset_info["asset_type"]
    if asset_type == "pdf":
        result = _extract_pdf_text(content_bytes)
    elif asset_type == "image":
        result = _extract_image_text(content_bytes)
    elif asset_type == "text":
        try:
            result = {
                "text": content_bytes.decode("utf-8", errors="replace"),
                "method": "utf8_text",
                "page_count": 1,
                "warnings": [],
            }
        except Exception as exc:
            result = {"text": "", "method": "text_error", "page_count": 1, "warnings": [str(exc)]}
    else:
        result = {
            "text": "",
            "method": "not_applicable",
            "page_count": None,
            "warnings": [],
        }

    result.update(asset_info)
    return result
