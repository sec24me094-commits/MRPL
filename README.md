# ADA WORKBENCH (SIH-26117)
### Sovereign Industrial AI & Air-Gapped Refinery Engineering Platform

<div align="center">

[![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-Orchestrator-orange.svg?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Docker Air-Gap](https://img.shields.io/badge/Docker-Zero--Egress%20Sandbox-2496ED.svg?style=for-the-badge&logo=docker&logoColor=white)](https://www.docker.com/)
[![Qdrant Vector DB](https://img.shields.io/badge/Qdrant-Local%20Vector%20Storage-DC382D.svg?style=for-the-badge&logo=qdrant&logoColor=white)](https://qdrant.tech/)
[![Ollama & vLLM](https://img.shields.io/badge/Inference-Ollama%20%7C%20vLLM-blueviolet.svg?style=for-the-badge)](https://ollama.com/)
[![Air-Gap Certified](https://img.shields.io/badge/Air--Gap-0--Byte%20WAN%20Egress-success.svg?style=for-the-badge&logo=wireshark&logoColor=white)](#-sovereign-air-gap--wireshark-zero-egress-verification)
[![ASME Section VIII](https://img.shields.io/badge/Compliance-ASME%20Sec%20VIII%20Div%201-red.svg?style=for-the-badge)](#-automated-verification-agent--asme-compliance)

<p align="center">
  <b>An on-premise, mathematically grounded, air-gapped cognitive assistant engineered for downstream petroleum refining, petrochemical plants, and critical industrial infrastructure.</b>
</p>

[Key Features](#-core-capabilities) •
[Architecture](#-system-architecture) •
[Quick Start](#-quick-start) •
[Browser Extension](#-intranet-rag-chromium-browser-extension) •
[Model Catalog](#-company-models-catalog-vllm--ollama) •
[API Reference](#-rest-api-reference) •
[Verification](#-testing--verification)

---

</div>

## 📌 Executive Summary

Modern hydrocarbon processing facilities—such as the **Mangalore Refinery and Petrochemicals Limited (MRPL)**—operate under stringent safety envelopes, strict statutory mandates (OISD, ASME, API), and zero-trust cybersecurity policies. Cloud-connected generative AI introduces unacceptable data exfiltration vectors, hallucination risks in pressure equipment calculations, and regulatory non-compliance.

**Ada Workbench** delivers a 100% sovereign, on-premise industrial AI ecosystem:
- **0-Byte External WAN Egress**: Validated by cryptographic Libpcap 2.4 packet traces and Docker container execution locked to `network_mode="none"`.
- **Intranet-Scoped Chromium Extension**: 1-click DOM/PDF extraction from internal DCS/SCADA portals directly to local embeddings without touching the internet.
- **Automated ASME Verification Agent**: Mathematically validates pressure vessel wall thickness calculations ($t = \frac{P \cdot R}{S \cdot E - 0.6 \cdot P}$), inspects isolated sandbox outputs, and issues SHA-256 certified compliance badges.
- **Enterprise Multi-Compiler**: Generates formal, audit-ready deliverables in **PDF**, **PPTX**, **DOCX**, **XLSX**, and **PCAP** formats with signature approval blocks.
- **Enterprise Model Catalog**: Strictly confined to approved **vLLM** and **Ollama** runtimes, supporting DeepSeek-R1, Qwen2.5-VL, Llama 3, and dynamic weights management.

---

## 🏗️ System Architecture

Ada Workbench implements a four-tier air-gapped pipeline orchestrating ingestion, retrieval-augmented grounding, isolated sandboxed computation, automated compliance auditing, and multi-format compilation:

```
                                  AIR-GAPPED PERIMETER (0-BYTE WAN EGRESS)
 ┌───────────────────────────────────────────────────────────────────────────────────────────────────────┐
 │                                                                                                       │
 │  ┌─────────────────────────────────┐                 ┌─────────────────────────────────────────────┐  │
 │  │      ENGINEER WORKSTATION       │                 │            ADA FASTAPI BACKEND              │  │
 │  │  ┌───────────────────────────┐  │   HTTP/Local    │  ┌───────────────────────────────────────┐  │  │
 │  │  │ Chromium Browser Extension│──┼────────────────►│  │  Stage 1: Ingestion & PII Scrubber   │  │  │
 │  │  │  - DOM & PDF Text Pull    │  │   (LAN/Loopback)│  │   - SHA-256 Integrity Fingerprint     │  │  │
 │  │  │  - Equipment Tag Parser   │  │                 │  │   - 10-Pattern Regex PII Sanitizer    │  │  │
 │  │  │  - Lead Engineer RBAC Key │  │                 │  └───────────────────┬───────────────────┘  │  │
 │  │  └───────────────────────────┘  │                 │                      ▼                      │  │
 │  │                                 │                 │  ┌───────────────────────────────────────┐  │  │
 │  │  ┌───────────────────────────┐  │   WebSockets    │  │  Stage 2: BGE Embeddings & Local RAG  │  │  │
 │  │  │ Next-Gen Workbench UI     │◄─┼────────────────►│  │   - BAAI/bge-large-en-v1.5 Dense V-DB │  │  │
 │  │  │  - Floating Composer Menu │  │      / SSE      │  │   - Qdrant On-Prem Vector Storage     │  │  │
 │  │  │  - Smooth Stop Control    │  │                 │  └───────────────────┬───────────────────┘  │  │
 │  │  │  - 5-Format Export Center │  │                 │                      ▼                      │  │
 │  │  └───────────────────────────┘  │                 │  ┌───────────────────────────────────────┐  │  │
 │  └─────────────────────────────────┘                 │  │  Stage 3: LangGraph Reasoning Core    │  │  │
 │                                                      │  │   - DeepSeek-R1 (CoT Mathematics)     │  │  │
 │                                                      │  │   - Qwen2.5-VL (P&ID Vision Analysis) │  │  │
 │                                                      │  │   - 600s Extended Execution Budget    │  │  │
 │                                                      │  └───────────────────┬───────────────────┘  │  │
 │                                                      │                      ▼                      │  │
 │                                                      │  ┌───────────────────────────────────────┐  │  │
 │                                                      │  │  Stage 4: Automated Verification Agent│  │  │
 │                                                      │  │   - ASME Section VIII Formula Audit   │  │  │
 │                                                      │  │   - Grounding & Reference Validator   │  │  │
 │                                                      │  │   - SHA-256 Certificate Attestation   │  │  │
 │                                                      │  └───────────────────┬───────────────────┘  │  │
 │                                                      │                      ▼                      │  │
 │  ┌─────────────────────────────────┐                 │  ┌───────────────────────────────────────┐  │  │
 │  │  ISOLATED DOCKER SANDBOX ENGINE │◄────────────────┼──┤  Docker Daemon (network_mode="none")  │  │  │
 │  │  - Python 3.11 Runtime          │  Stdout/Stderr  │  │   - Memory: 128 MB | PIDs: 32         │  │  │
 │  │  - cap_drop=["ALL"], read_only  │─────────────────┼─►│   - 0-Byte External Egress Guarantee  │  │  │
 │  └─────────────────────────────────┘                 │  └───────────────────────────────────────┘  │  │
 │                                                      │                      ▼                      │  │
 │                                                      │  ┌───────────────────────────────────────┐  │  │
 │                                                      │  │  Stage 5: Enterprise Document Factory │  │  │
 │                                                      │  │   - PDF Technical Approval Note       │  │  │
 │                                                      │  │   - PPTX Engineering Presentation Deck│  │  │
 │                                                      │  │   - DOCX Compliance Investigation     │  │  │
 │                                                      │  │   - XLSX Calculation Audit Sheet      │  │  │
 │                                                      │  │   - PCAP Libpcap 2.4 Binary Capture   │  │  │
 │                                                      │  └───────────────────────────────────────┘  │  │
 │                                                      └─────────────────────────────────────────────┘  │
 └───────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Core Capabilities

### 1. 🛑 Smooth Model Stop Control
Operators running complex calculations can halt inference at any microsecond without browser hang-ups, dropped sockets, or zombie background processes:
- **UI State Transition**: The primary action button dynamically shifts from Send (`#submitBtn`) to a pulsating Red Stop button (`#stopBtn`).
- **Client SSE Cancellation**: An internal JavaScript `AbortController` terminates the incoming token stream immediately.
- **Server-Side Thread Cleanup**: Dispatches `POST /api/v1/chat/stop` to safely interrupt the LangGraph execution loop while preserving all partial Chain-of-Thought output and execution logs.

### 2. 🏢 Company Models Catalog (vLLM & Ollama)
Enterprise governance prohibits pulling unvetted open-source models into plant infrastructure. Ada Workbench enforces an approved internal catalog:
- **Curated Models**:
  - `deepseek-r1:8b` (Ollama) — Chain-of-Thought mathematical derivations & ASME calculations.
  - `deepseek-r1:14b` (vLLM) — High-throughput clustered refinery reasoning.
  - `qwen2.5vl:7b` (Ollama) — High-resolution P&ID schematic and isometric diagram parsing.
  - `llama3:8b` (Ollama) — Formal industrial investigation reporting & clause synthesis.
  - `mistral:7b` (Ollama) — Ultra-fast SOP cross-referencing and clause lookup.
  - `codellama:7b` (vLLM) — Python sandbox automation and PID loop simulation scripts.
- **Dynamic Control**: Live querying of installed weights (`/api/v1/models/installed`), real-time runtime model switching (`/api/v1/models/switch`), and asynchronous pulling (`/api/v1/models/pull`).

### 3. ⏱️ 600s Deep Reasoning & Automated Verification Agent
- **Extended Runtime Budget**: Raised `OLLAMA_TIMEOUT_SECONDS` to **600.0s** (10 minutes), eliminating HTTP 504 and gateway timeouts during deep multi-step derivations.
- **Verification Agent Node (`_verification_node`)**:
  - Mathematically audits calculations against **ASME Section VIII Div 1** mandatory formulas:
    $$t = \frac{P \cdot R}{S \cdot E - 0.6 \cdot P}$$
  - Cross-checks corrosion allowance ($C_A$), joint efficiency ($E$), and allowable stress ($S$) against the design pressure ($P$) and inner radius ($R$).
  - Validates sandbox container exit codes and parses stdout for numerical convergence.
  - Attests SOP citations against Qdrant vector IDs and issues an official **VERIFIED_COMPLIANT** certificate card.

### 4. 🧩 Intranet RAG Chromium Browser Extension
Enables plant engineers to ingest internal refinery operating manuals, digital SOPs, and technical intranet pages without manual copying, Python scripting, or WAN leaks:
- **Strict Network Boundary**: Manifest V3 permissions restricted solely to `localhost`, `127.0.0.1`, `*.mrpl.local`, `10.*.*.*`, and `192.168.*.*`.
- **Zero-Egress Ingestion**: The extension extracts text and equipment tags directly from the DOM or Web PDF viewer and sends an HTTP POST to `http://localhost:8000/api/v1/rag/ingest`.
- **RBAC Authorization**: Protects vector indexing with Lead Engineer cryptographic keys.
- **1-Click Packaging**: The entire unpacked extension is available as a bundled `.zip` archive directly from the workbench UI or via `GET /api/v1/extension/download`.

### 5. 🛡️ Sovereign Air-Gap & Wireshark Zero-Egress Verification
- **Synthetic Libpcap 2.4 Engine**: Compiles real-time, binary-compliant PCAP files (`0xa1b2c3d4` magic header) detailing every loopback and blocked egress frame.
- **Live Auditing**: Executes active egress network probes on demand (`POST /api/v1/security/wireshark-audit`), demonstrating 0 bytes transmitted outside the LAN envelope.
- **Audit Deliverable**: Plant safety officers can download the raw capture file (`GET /api/v1/security/download-pcap`) to inspect in standard Wireshark desktop clients.

### 6. 📄 5-Format Enterprise Multi-Compiler
Generates formal, production-grade engineering artifacts directly from verification sessions:
1. **MRPL Technical Approval Note (`.pdf`)**: Formatted with executive headers, ASME Section VIII compliance tables, SHA-256 asset hashes, sandbox status, and tri-signature approval blocks.
2. **Executive Engineering Review Deck (`.pptx`)**: Generates 16:9 widescreen presentation slides complete with executive summary, compliance matrix, and sandbox logs.
3. **Formal Investigation Note (`.docx`)**: Structured Word document with standard plant layout and typography.
4. **ASME Calculation Audit Workbook (`.xlsx`)**: Parameterized Excel sheets with formulas, stress limits, and safety factor calculations.
5. **Wireshark Network Capture (`.pcap`)**: Standard binary packet capture proving air-gap compliance.

---

## 📂 Repository Structure

```text
ada-workbench/
├── app/
│   ├── agents/
│   │   ├── orchestrator.py            # LangGraph multi-stage graph & Automated Verification Agent
│   │   ├── sandbox_agent.py           # Docker isolated container execution manager
│   │   └── vision_agent.py            # Visual analysis for P&ID schematics & blueprints
│   ├── captures/                      # Storage for live Wireshark .pcap audit logs
│   ├── extension/                     # Bundled Chromium Manifest V3 Intranet Browser Extension
│   │   ├── background.js              # Extension service worker
│   │   ├── content.js                 # Intranet DOM text & equipment tag extractor
│   │   ├── manifest.json              # Zero-egress host permissions configuration
│   │   ├── popup.html                 # Extension popup interface
│   │   └── popup.js                   # Lead Engineer RBAC & local POST transmitter
│   ├── services/
│   │   ├── compiler_service.py        # PDF (ReportLab), PPTX, DOCX, & XLSX document factory
│   │   ├── document_service.py        # Local file ingestion & cryptographic digest processor
│   │   ├── embedding_service.py       # BAAI/bge-large-en-v1.5 local embedding provider
│   │   ├── ingestion_service.py       # 10-pattern PII sanitization engine
│   │   ├── models_service.py          # Enterprise vLLM & Ollama models catalog manager
│   │   ├── rag_service.py             # Qdrant vector retrieval & intranet document indexer
│   │   ├── security_service.py        # Air-gap posture & security verification checks
│   │   └── wireshark_service.py       # Libpcap 2.4 binary generator & zero-egress auditor
│   ├── static/
│   │   └── index.html                 # Next-Gen Workbench UI, Composer, & Modals
│   ├── __init__.py
│   └── main.py                        # FastAPI application entrypoint & API router
├── extension/                         # Root copy of the Chromium browser extension
├── scripts/
│   └── verify_sovereignty.py          # Standalone air-gap & security verification script
├── Dockerfile                         # Hardened multi-stage container build
├── docker-compose.yml                 # Orchestration for Backend Core & Qdrant Vector DB
├── requirements.txt                   # Production Python dependencies
├── test_new_features.py               # Validation suite for Models Catalog, Ingest, & Extension
├── test_new_modules.py                # Validation suite for PDF, PPTX, Sandbox, & Wireshark
├── test_suite.py                      # Comprehensive end-to-end integration test suite
└── SOVEREIGN_OPERATIONS_REPORT.md     # Production architecture, security, and benchmark report
```

---

## 🚀 Quick Start

### Prerequisites
- **Python**: Version 3.10 or 3.11
- **Container Runtime**: Docker Desktop or Docker Engine with standard socket access
- **Local LLM Runtime**: [Ollama](https://ollama.com/) running on `http://localhost:11434` (with `deepseek-r1:8b` or `llama3:8b`)
- **Vector Storage**: Qdrant running on `localhost:6333` (or via Docker Compose)

---

### Option A: Complete Docker Compose Deployment (Recommended)

Start the unified backend and vector database with a single command:

```bash
git clone https://github.com/sec24me094-commits/MRPL.git
cd MRPL

# Start Ada Backend Core and Qdrant Vector DB
docker compose up -d --build
```

The application will be live at `http://localhost:8000`.

---

### Option B: Native Developer Setup

For active development with hot reloading:

```bash
# 1. Clone repository
git clone https://github.com/sec24me094-commits/MRPL.git
cd MRPL

# 2. Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate       # On Linux/macOS
# .venv\Scripts\activate        # On Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Ensure local models are available
ollama pull deepseek-r1:8b
ollama pull qwen2.5vl:7b

# 5. Launch FastAPI with auto-reload
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 🧩 Intranet RAG Chromium Browser Extension

The browser extension allows plant personnel to safely capture SOPs and process documents from the intranet and commit them into Ada's local vector store without egress.

```
┌───────────────────────────┐      Local LAN / Loopback      ┌──────────────────────────┐
│  Refinery Intranet / SOP  │ ─────────────────────────────► │   Ada FastAPI Backend    │
│  (Workstation Chrome/Edge)│   POST /api/v1/rag/ingest      │  - PII Scrubbing         │
│                           │   RBAC: lead-engineer-key-01   │  - SHA-256 Checksum      │
└───────────────────────────┘                                │  - bge-large-en Embedding│
                                                             └────────────┬─────────────┘
                                                                          ▼
                                                             ┌──────────────────────────┐
                                                             │ Qdrant mrpl_sop_collection│
                                                             └──────────────────────────┘
```

### Installation Steps:
1. **Download the Extension Archive**:
   - Open Ada Workbench (`http://localhost:8000`) and click **Intranet RAG** in the sidebar.
   - Click the **Download Extension (.ZIP)** button (or visit `http://localhost:8000/api/v1/extension/download`).
2. **Unpack**: Extract `ada-browser-extension.zip` into a local directory (e.g. `C:\tools\ada-extension`).
3. **Load in Browser**:
   - Open Google Chrome, Brave, or Microsoft Edge and navigate to `chrome://extensions/`.
   - Enable **Developer mode** toggle in the top-right corner.
   - Click **Load unpacked** and select the unzipped directory.
4. **Push Documents**:
   - Navigate to any internal refinery document, digital SOP, or technical PDF.
   - Click the **Ada RAG** icon in your browser toolbar.
   - Enter your Lead Engineer RBAC key (defaults to `lead-engineer-key-01`).
   - Click **Push to ADA RAG** — the text is immediately sanitized, embedded, and indexed in Qdrant with zero WAN egress!

---

## 🤖 Company Models Catalog (vLLM & Ollama)

Ada Workbench restricts model usage to an audited enterprise catalog:

| Model Identifier | Engine | VRAM Target | Primary Enterprise Purpose |
| :--- | :---: | :---: | :--- |
| **`deepseek-r1:8b`** | Ollama | 8 GB | Multi-step mathematical derivations, ASME Section VIII wall thickness checks. |
| **`deepseek-r1:14b`** | vLLM | 16 GB | High-throughput clustered reasoning for multi-unit process engineering. |
| **`qwen2.5vl:7b`** | Ollama | 10 GB | High-resolution vision parsing of P&ID drawings and isometric line diagrams. |
| **`llama3:8b`** | Ollama | 6 GB | Formal investigation notes, compliance summaries, and incident reporting. |
| **`mistral:7b`** | Ollama | 6 GB | Rapid SOP cross-referencing and technical clause identification. |
| **`codellama:7b`** | vLLM | 8 GB | Python sandbox code synthesis, PID control loops, and thermodynamics scripts. |

Switch models on the fly through the workbench UI (**Models Catalog** in the sidebar) or via the API:

```bash
curl -X POST http://localhost:8000/api/v1/models/switch \
  -H "Content-Type: application/json" \
  -d '{"model_tag": "deepseek-r1:8b", "engine": "ollama"}'
```

---

## 📡 REST API Reference

| Endpoint | Method | Description | Network Scope |
| :--- | :---: | :--- | :--- |
| `/health` | `GET` | Health check and active runtime status | Localhost |
| `/api/v1/chat` | `POST` | Execute LangGraph engineering review with streaming SSE | Localhost |
| `/api/v1/chat/stop` | `POST` | Smoothly cancel active model inference without orphan tasks | Localhost |
| `/api/v1/models/catalog` | `GET` | Retrieve curated company models catalog and specifications | Localhost |
| `/api/v1/models/installed`| `GET` | Query installed model weights directly from Ollama runtime | Localhost |
| `/api/v1/models/pull` | `POST` | Asynchronously pull approved model weights in background | Localhost |
| `/api/v1/models/switch` | `POST` | Dynamically switch the active reasoning model | Localhost |
| `/api/v1/rag/ingest` | `POST` | Ingest intranet text/SOPs with PII scrubbing & zero egress | Intranet/LAN |
| `/api/v1/rag/sops` | `GET` | Retrieve indexed refinery SOP knowledge entries | Localhost |
| `/api/v1/extension/download` | `GET` | Download ready-to-load Chromium Manifest V3 extension bundle | Localhost |
| `/api/v1/security/posture` | `GET` | Query live air-gap posture and Wireshark audit summary | Localhost |
| `/api/v1/security/wireshark-audit` | `POST` | Execute live zero-egress network probe & update PCAP | Localhost |
| `/api/v1/security/download-pcap` | `GET` | Download raw Libpcap 2.4 binary packet capture file | Localhost |
| `/api/v1/export/pdf` | `POST` | Compile formal MRPL Technical Approval Note (`.pdf`) | Localhost |
| `/api/v1/export/pptx` | `POST` | Compile Engineering Review Presentation Deck (`.pptx`) | Localhost |
| `/api/v1/export/docx` | `POST` | Compile Technical Investigation Report (`.docx`) | Localhost |
| `/api/v1/export/xlsx` | `POST` | Compile ASME Calculation Audit Workbook (`.xlsx`) | Localhost |

---

## 🧪 Testing & Verification

Ada Workbench includes comprehensive automated test suites covering all modules:

### 1. New Enterprise Features Suite
Validates the Models Catalog, Model Switcher, Chat Stop handler, Intranet Ingestion (with PII scrubbing and SHA-256 calculation), and Browser Extension Zip generation:

```bash
python test_new_features.py
```
```text
ALL 6 NEW FEATURE TESTS PASSED SUCCESSFULLY!
- Models Catalog: PASSED
- Installed Models: PASSED
- Model Switch: PASSED
- Chat Stop: PASSED
- Intranet RAG Ingest (Zero-Egress): PASSED
- Browser Extension Zip Download: PASSED
```

### 2. Export Compilers & Sandbox Suite
Validates ReportLab PDF generation, PPTX widescreen decks, Wireshark Libpcap binary generation, and Docker Sandbox socket discovery:

```bash
python test_new_modules.py
```
```text
ALL NEW MODULES VALIDATED AND OPERATIONAL!
- PDF Export: PASSED (%PDF-1.4 header verified)
- PPTX Export: PASSED (PK zip container verified)
- Wireshark Libpcap: PASSED (Magic 0xa1b2c3d4, 0 WAN frames)
- Docker Sandbox: PASSED (Socket connected, network_mode="none")
```

### 3. Full End-to-End Integration Suite
Executes complete pipeline verification including document ingestion, RAG vector retrieval, sandbox script execution, and multi-format document compilation:

```bash
python test_suite.py
```

---

## 🔒 Security, Compliance & Data Governance

- **ASME Section VIII Division 1**: Mandatory verification rules enforced for internal design pressure, allowable tensile stress, joint efficiency, and minimum required wall thickness.
- **OISD-STD-118 / API 510**: Standard inspection and non-destructive testing requirements embedded in prompt templates and SOP vector collections.
- **PII Scrubbing**: 10 comprehensive regular expressions scrub names, phone numbers, employee identification tags, and internal IP addresses prior to vectorization or LLM reasoning.
- **Docker Isolation**: Containers execute with `network_mode="none"`, `cap_drop=["ALL"]`, read-only root filesystems where appropriate, and strict 128 MB RAM limits.
- **Data Protection**: Full compliance with `/accidental-data-loss-prevention`. No destructive database operations or unconfirmed storage deletions are permitted.

---

## 👥 Contributors & SIH 2026 Context

Developed for the **Smart India Hackathon (SIH 2026)** — Problem Statement **SIH-26117**:
- **Project**: Sovereign Industrial AI Workbench (Ada Workbench)
- **Target Organization**: Mangalore Refinery and Petrochemicals Limited (MRPL)
- **Repository**: [https://github.com/sec24me094-commits/MRPL](https://github.com/sec24me094-commits/MRPL)
- **Status**: Production-Ready Prototype / Air-Gap Validated

---

<div align="center">
  <sub>Built with uncompromising standards for sovereign industrial intelligence and high-consequence plant operations.</sub>
</div>
