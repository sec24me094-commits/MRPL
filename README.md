# Ada Workbench

Ada Workbench is a sovereign on-premise industrial AI workbench designed for refinery engineering review workflows. The project demonstrates a staged approach to:

- ingesting uploaded blueprints and notes
- scrubbing sensitive PII and hashing the source asset
- grounding reasoning against local SOP references
- routing prompts to multimodal and reasoning models
- executing generated Python calculation blocks inside an air-gapped Docker sandbox
- compiling formal approval-note and calculation-sheet outputs

## Project structure

- `app/` — FastAPI backend and agent modules
- `app/services/` — ingestion, RAG, and compiler services
- `app/agents/` — orchestration, vision, and sandbox execution logic
- `app/static/` — browser UI
- `docker-compose.yml` — local service orchestration for Qdrant and the backend
- `Dockerfile` — backend application container
- `requirements.txt` — Python dependency list
- `test_suite.py` — repository validation suite

## Quick start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the local services:
   ```bash
   docker compose up --build
   ```
3. Run the validation suite:
   ```bash
   python test_suite.py
   ```
4. Open the app at `http://localhost:8000`.

## Notes

This repository is intended for demonstration and on-premise engineering workflows. It assumes local access to Ollama, Docker, and Qdrant, and uses an air-gapped container sandbox for code execution safety.
