# ADA Workbench — Sovereign Operations Report

## 1. Purpose

ADA Workbench is a local engineering decision-support system for P&IDs,
blueprints, refinery SOPs, calculations, and review artifacts. The intended
deployment boundary is a plant-controlled host or isolated plant network:

- Ollama serves Qwen2.5-VL and DeepSeek-R1 locally.
- Qdrant stores the local refinery knowledge base.
- BGE-large embeddings are loaded from a provisioned local model directory.
- Generated calculations run in ephemeral Docker containers with
  `network_mode=none`.
- DOCX, XLSX, and PPTX artifacts are generated on the ADA host.

ADA does not replace the responsible engineer, plant approval process, host
firewall, or independent network audit.

## 2. What was built in this implementation pass

| Area | Implementation | Operational state |
| --- | --- | --- |
| File gateway | Added multipart `/api/v1/ingest/file`, size/type validation, PDF/image/text classification, and extraction metadata. | Ready after dependency install |
| PII redaction | Regex scrubbing now applies to operator notes and locally extracted document text. | Ready; expand plant-specific patterns |
| PDF/OCR | Added local `pypdf`, `pdf2image`, and `pytesseract` integration with explicit warnings when tooling is absent. | Ready after Tesseract/Poppler validation |
| SHA-256 | Hashes original uploaded bytes and returns the digest in the manifest. | Complete |
| LangGraph | Replaced the linear orchestrator with explicit route, retrieve, vision, reason, execute, correct, and finalize nodes. | Complete in code |
| BGE-large | Added an offline-only local model adapter; it never downloads weights at runtime. | Ready after local model provisioning |
| Qdrant RAG | Added real BGE vector seeding/search in a new collection; lexical retrieval remains an explicit fallback. | Vector mode depends on BGE + Qdrant |
| PPTX | Added `/api/v1/export/pptx` and a review-deck compiler. | Ready after `python-pptx` install |
| Seccomp | Sandbox now explicitly requests Docker's `default` seccomp profile. | Configuration evidence; validate on target daemon |
| Sovereignty report | Added `/api/v1/security/posture` and `scripts/verify_sovereignty.py`. | Ready for acceptance testing |

The application intentionally reports degraded/unverified conditions instead of
claiming that an unavailable model, OCR runtime, vector model, or sandbox has
completed work.

## 3. Runtime flow

```text
Operator upload
      |
      v
Stage 1: validate -> SHA-256 -> local PDF/OCR/text extraction -> PII scrub
      |
      v
Stage 2: LangGraph route
      |-------------------------------|
      v                               v
Qwen2.5-VL vision branch       BGE/Qdrant retrieval -> DeepSeek-R1
                                      |
                                      v
                              Python block detected?
                                      |
                                      v
Stage 3: ephemeral Docker sandbox, network_mode=none, resource/security limits
                                      |
                         failure -> DeepSeek correction loop (max 2)
                                      |
                                      v
Stage 4: DOCX approval note / XLSX calculations / PPTX review deck
```

## 4. Sovereign installation

Use an internal package mirror or a pre-staged wheelhouse. Do not allow the
production host to resolve packages from the public Internet.

### 4.1 Prepare offline assets

Place the BGE model at:

```text
ada-workbench/models/bge-large-en-v1.5/
```

The directory must contain the complete local Sentence Transformers model. The
model path is configured by `ADA_BGE_MODEL_PATH`; the compose file maps it to
`/app/models` read-only.

Provision the Ollama model files through the organization's approved offline
model transfer process. Verify locally with:

```powershell
ollama list
```

Expected identifiers are `qwen2.5-vl:7b` and `deepseek-r1:8b`, or the
values explicitly configured by the deployment.

### 4.2 Install dependencies without Internet access

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --no-index --find-links .\wheelhouse -r requirements.txt
```

The Docker build installs `poppler-utils` and `tesseract-ocr` for local PDF
and image OCR. Validate the Tesseract language packs required by the plant.

### 4.3 Start the sovereign services

```powershell
docker compose up -d ada-vector-db ada-backend-core
docker compose ps
```

The backend requires access to the Docker socket for ephemeral calculation
containers. On Linux, grant the backend process the socket's dedicated group
without making the application container broadly privileged. On Docker Desktop,
verify the socket integration and Docker Desktop policy before production.

## 5. Operator procedure

1. Open `http://127.0.0.1:8000` from the controlled workstation.
2. Upload a P&ID, blueprint, PDF, or engineering note.
3. Confirm the displayed SHA-256 digest and ingestion state.
4. Review the extraction method. `pypdf_text_layer`, `pdf_ocr`, and
   `image_ocr` mean local extraction; an `*_unavailable` or `*_failed`
   warning means the text evidence is incomplete.
5. Ask a focused engineering question. For drawings, use the vision route; for
   limits, calculations, and compliance checks, use the reasoning route.
6. Inspect SOP identifiers, model route, verification status, and sandbox output.
   A model response without successful sandbox execution is not a verified
   calculation.
7. Export the approval note, calculations sheet, or review deck.
8. A qualified engineer reviews the source, assumptions, SOP clauses, output,
   and signatures before any plant action.

## 6. API runbook

| Endpoint | Use |
| --- | --- |
| `GET /health` | Service, Qdrant, and embedding readiness |
| `GET /api/v1/security/posture` | Security configuration and evidence boundary |
| `POST /api/v1/ingest` | JSON/Base64 ingestion |
| `POST /api/v1/ingest/file` | Native multipart file ingestion |
| `POST /api/v1/chat` | LangGraph routing, local RAG, model response, sandbox evidence |
| `POST /api/v1/vision/analyze` | Direct multipart Qwen2.5-VL analysis |
| `GET /api/v1/rag/sops` | SOP records and vector/lexical retrieval status |
| `POST /api/v1/export/docx` | Approval note |
| `POST /api/v1/export/xlsx` | Calculation workbook |
| `POST /api/v1/export/pptx` | Engineering review deck |

Example health checks:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/api/v1/security/posture
python scripts/verify_sovereignty.py --api http://127.0.0.1:8000
```

## 7. Security and egress boundary

The calculation sandbox has these controls:

- `network_mode=none`
- ephemeral container removal
- memory limit and PID limit
- `cap_drop=ALL`
- `no-new-privileges:true`
- Docker `seccomp=default`

The supplied probe checks socket blocking inside one tested container namespace.
It does not prove that the host, Docker daemon, Ollama, Qdrant, or workstation
emitted zero packets. For acceptance, retain:

1. host firewall rules for permitted plant-local endpoints;
2. Docker daemon and socket policy;
3. a Wireshark or `tcpdump` capture during the sandbox probe;
4. SHA-256 inventory for model files and container images;
5. JSON output from `scripts/verify_sovereignty.py`.

The accurate claim is “sandbox calculation egress blocked; backend accesses
approved local services,” not “the entire system has zero network traffic.”

## 8. Acceptance checklist

- [ ] Offline wheelhouse installed successfully.
- [ ] Ollama models loaded locally and tested with public-network access disabled.
- [ ] BGE model directory exists and `/health` reports `available: true`.
- [ ] Qdrant reports `vector_search_available: true`.
- [ ] A text-layer PDF extracts locally.
- [ ] A scanned PDF/image produces OCR or an explicit warning.
- [ ] PII test data is redacted from notes and extracted text.
- [ ] Ingested asset SHA-256 is recorded in the review bundle.
- [ ] LangGraph route and correction events appear in application logs.
- [ ] Sandbox probe passes and host-level packet capture is retained.
- [ ] DOCX, XLSX, and PPTX files open with session evidence.
- [ ] A responsible engineer signs the final review artifact.

## 9. Known limits before production

- The sample SOP set is demonstration data; replace it with approved plant
  documents and a controlled ingestion/signing process.
- Regex redaction is not a complete data-loss-prevention system. Add plant
  names, badge formats, identifiers, and classification labels.
- OCR accuracy must be measured against plant drawing quality and fonts.
- The application does not perform the Wireshark capture itself.
- The UI is not an approval authority; human sign-off remains mandatory.

