# Ada Workbench

Ada Workbench is a sovereign, on-premise engineering AI platform built for refinery and industrial operations review. It combines secure data ingestion, local knowledge retrieval, multimodal analysis, sandboxed computation, and formal document generation into a single production-oriented workflow.

The solution is designed for scenarios where plant engineering teams need to analyse P&IDs, process blueprints, operating notes, and compliance requirements without exposing sensitive assets to external systems.

## Why this project exists

Modern plants generate large volumes of engineering artifacts and compliance evidence. Ada Workbench addresses this by providing a controlled workflow for:

- secure upload and provenance tracking of technical assets
- privacy-aware sanitisation of operator and inspection metadata
- retrieval of local SOP and design-limit knowledge
- routing of engineering questions to the correct specialist model
- code-based verification in an isolated sandbox
- export of formal investigation outputs in structured formats

## Core capabilities

### 1. Secure ingestion pipeline
- Computes SHA-256 digests for uploaded engineering documents and schematics
- Sanitises PII, employee IDs, private IP addresses, and operator notes
- Generates a traceable ingestion manifest for downstream use

### 2. Local SOP grounding
- Uses a local knowledge store to retrieve relevant refinery procedures and technical thresholds
- Grounds reasoning against equipment-specific rules and design limits
- Supports deterministic fallback when external services are unavailable

### 3. Multimodal and reasoning workflow
- Routes image-based queries to vision analysis for schematic interpretation
- Directs calculation and compliance questions to reasoning models grounded in local SOP context
- Extracts executable Python logic from AI output when numerical verification is required

### 4. Air-gapped execution sandbox
- Runs generated Python inside Docker with `network_mode="none"`
- Limits execution time, memory, and process count for safety
- Captures stdout, stderr, and error taxonomy for self-correction loops

### 5. Formal output generation
- Produces MRPL-style technical approval notes in `.docx`
- Produces calculation audit tables in `.xlsx`
- Includes hash attestation and operational metadata in generated artifacts

## Architecture overview

The application is organised into four stages:

1. Stage 1 — Ingestion Gateway
   - asset ingestion
   - cryptographic hashing
   - PII scrubbing
   - manifest creation

2. Stage 2 — Knowledge and Reasoning Core
   - RAG-based SOP retrieval
   - model routing
   - industrial reasoning

3. Stage 3 — Sandboxed Execution
   - Python validation in isolated container runtime
   - self-correction and auditability

4. Stage 4 — Secure Output Compilation
   - official documentation and calculation sheets

## Repository structure

```text
ada-workbench/
├── app/
│   ├── agents/
│   │   ├── orchestrator.py
│   │   ├── sandbox_agent.py
│   │   └── vision_agent.py
│   ├── services/
│   │   ├── compiler_service.py
│   │   ├── ingestion_service.py
│   │   └── rag_service.py
│   ├── static/
│   │   └── index.html
│   ├── __init__.py
│   └── main.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── test_suite.py
├── .gitignore
├── README.md
└── .dockerignore
```

## Prerequisites

Before running the project locally, ensure you have:

- Python 3.10+
- Docker Desktop or a compatible Docker runtime
- access to a local Ollama instance for model inference
- a local Qdrant instance or the bundled compose setup

## Quick start

### 1. Clone the repository

```bash
git clone https://github.com/sec24me094-commits/MRPL.git
cd MRPL
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the local services

```bash
docker compose up --build
```

This starts the backend service and the Qdrant vector database used for local knowledge retrieval.

### 4. Run the test suite

```bash
python test_suite.py
```

### 5. Start the FastAPI service locally

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Then open:

```text
http://localhost:8000
```

## Key API endpoints

The application exposes the following primary endpoints:

- `GET /health` — service health status
- `POST /api/v1/ingest` — ingest and secure an uploaded asset
- `POST /api/v1/chat` — execute the orchestrated engineering workflow
- `GET /api/v1/rag/sops` — retrieve SOP knowledge entries
- `POST /api/v1/export/docx` — export the approval note
- `POST /api/v1/export/xlsx` — export the calculation workbook

## Environment configuration

The project supports several environment variables for deployment flexibility:

```bash
OLLAMA_BASE_URL=http://host.docker.internal:11434
OLLAMA_TIMEOUT_SECONDS=180.0
QDRANT_HOST=localhost
QDRANT_PORT=6333
SANDBOX_TIMEOUT_SECONDS=10
SANDBOX_MEMORY_LIMIT=128m
```

## Security and operational model

Ada Workbench is designed for controlled on-premise execution:

- no outbound network access in the execution sandbox
- local RAG grounding for compliance evidence
- SHA-256 attestation for engineering artifacts
- deterministic handling of confidential metadata in operator notes
- structured operational logs for review and audit trails

## Testing and validation

The project includes a validation suite in `test_suite.py` covering:

- Stage 1 ingestion and sanitisation
- Stage 2 SOP retrieval and local grounding
- Stage 3 sandbox execution checks
- Stage 4 document generation
- end-to-end API validation

## License

This project is provided as an internal engineering demonstration and on-premise research platform. Please review usage boundaries and confidentiality requirements before deployment in production environments.

## Contact / project context

This repository represents an industrial AI prototype for sovereign refinery engineering assistance, with emphasis on secure local operation, compliance grounding, and document-ready verification workflows.
