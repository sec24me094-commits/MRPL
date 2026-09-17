"""
Stage 1: Input & Ingestion Gateway - Ada Workbench (SIH 26117)
Provides PII scrubbing, confidential metadata redaction, and cryptographic SHA-256 hashing
for all uploaded P&IDs, blueprints, vendor datasheets, and operator notes.
"""

import hashlib
import logging
import re
import time
from typing import Any, Dict, List, Tuple

from app.services.document_service import extract_local_text

logger = logging.getLogger("ada_workbench.ingestion")

# PII & Confidentiality Regex Patterns
PII_PATTERNS: List[Tuple[str, re.Pattern, str]] = [
    # Email addresses
    (
        "EMAIL",
        re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),
        "[REDACTED_EMAIL]",
    ),
    # Indian / International Phone Numbers
    (
        "PHONE",
        re.compile(r"(?:\+?91[\-\s]?)?[6-9]\d{9}\b|\b\d{3}[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "[REDACTED_PHONE]",
    ),
    # Employee / Contractor Badges (e.g., MRPL-EMP-8492, CONT-9812)
    (
        "EMPLOYEE_ID",
        re.compile(r"\b(?:MRPL|EMP|CONT|OPERATOR|BADGE)[-_]?\d{4,8}\b", re.IGNORECASE),
        "[REDACTED_BADGE_ID]",
    ),
    # Internal IP Addresses (IPv4 private ranges)
    (
        "INTERNAL_IP",
        re.compile(r"\b(?:10\.\d{1,3}|192\.168\.\d{1,3}|172\.(?:1[6-9]|2\d|3[0-1]))\.\d{1,3}\b"),
        "[REDACTED_INTERNAL_IP]",
    ),
    # Signatures / Inspector Name tags (e.g., Approved By: John Doe, Inspected By: Jane)
    (
        "INSPECTOR_NAME",
        re.compile(r"(?:Approved|Inspected|Drawn|Checked|Verified)\s+By\s*:\s*([A-Za-z\s\.]{2,25})", re.IGNORECASE),
        "Approved By: [REDACTED_PERSONNEL]",
    ),
]


def compute_sha256(content_bytes: bytes) -> str:
    """
    Computes a cryptographic SHA-256 digest of raw asset bytes.
    Enforces immutable provenance and tamper-evident audit trails.
    """
    hasher = hashlib.sha256()
    hasher.update(content_bytes)
    return hasher.hexdigest()


def scrub_pii(text: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    Scans text for personal identifiable information (PII) and sensitive internal telemetry,
    redacting matches according to MRPL security protocols.

    Returns:
        Tuple[str, List[Dict[str, Any]]]: (sanitized_text, list_of_redactions)
    """
    sanitized = text
    redaction_log: List[Dict[str, Any]] = []

    for label, pattern, replacement in PII_PATTERNS:
        matches = pattern.findall(sanitized)
        if matches:
            count = len(matches)
            # Preserve the original personnel label while replacing only the
            # identified name. A static "Approved By" replacement would alter
            # the meaning of "Inspected By" and "Checked By" records.
            if label == "INSPECTOR_NAME":
                sanitized = pattern.sub(
                    lambda match: f"{match.group(0).split(':', 1)[0]}: [REDACTED_PERSONNEL]",
                    sanitized,
                )
            else:
                sanitized = pattern.sub(replacement, sanitized)
            redaction_log.append({
                "type": label,
                "occurrences": count,
                "replacement": replacement,
            })
            logger.info("Stage 1 Ingestion: Scrubbed %d instances of %s", count, label)

    return sanitized, redaction_log


def process_uploaded_asset(
    filename: str,
    content_bytes: bytes,
    optional_text_notes: str = "",
    content_type: str = "",
) -> Dict[str, Any]:
    """
    Full Stage 1 Ingestion Pipeline:
    1. Cryptographic SHA-256 asset attestation.
    2. PII / Confidentiality scrubbing on accompanying notes or text layers.
    3. Structured ingestion manifest generation for Stage 2 orchestrator.

    Args:
        filename (str): Name of uploaded P&ID or blueprint file.
        content_bytes (bytes): Raw binary data of the file.
        optional_text_notes (str): Operator remarks or extracted OCR text.

    Returns:
        Dict[str, Any]: Ingestion manifest including checksum, size, and PII status.
    """
    logger.info("Initiating Stage 1 Ingestion for file: %s (%d bytes)", filename, len(content_bytes))

    # 0. Local document inspection.  The extractor is offline-only and returns
    # an explicit warning when a parser/OCR runtime is not provisioned.
    extraction = extract_local_text(filename, content_bytes, content_type or None)
    extracted_text = extraction.get("text", "")
    combined_text = "\n\n".join(
        part.strip() for part in (optional_text_notes or "", extracted_text) if part and part.strip()
    )

    # 1. Cryptographic SHA-256 Hashing
    sha256_hash = compute_sha256(content_bytes)

    # 2. PII Scrubbing
    scrubbed_notes, redactions = scrub_pii(combined_text)

    # 3. Build Sovereign Ingestion Manifest
    manifest = {
        "status": "ingested_and_secured",
        "stage": 1,
        "filename": filename,
        "byte_size": len(content_bytes),
        "sha256_digest": sha256_hash,
        "asset_type": extraction.get("asset_type", "binary"),
        "content_type": extraction.get("content_type"),
        "text_extraction": {
            "method": extraction.get("method", "not_applicable"),
            "page_count": extraction.get("page_count"),
            "warnings": extraction.get("warnings", []),
            "characters_extracted": len(extracted_text),
        },
        "pii_scrubbed": len(redactions) > 0,
        "redaction_count": sum(r["occurrences"] for r in redactions),
        "redactions": redactions,
        "sanitized_notes": scrubbed_notes,
        "sanitized_extracted_text": scrub_pii(extracted_text)[0] if extracted_text else "",
        # Ingestion can attest to the asset hash and redaction activity, but
        # it cannot independently prove the deployment network perimeter.
        "airgap_verified": False,
        "airgap_status": "not_verified_by_ingestion",
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    logger.info(
        "Stage 1 Ingestion Complete. Asset: %s | SHA-256: %s... | PII Redactions: %d",
        filename,
        sha256_hash[:12],
        manifest["redaction_count"],
    )

    return manifest
