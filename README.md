# HyperDoc

## Agentic Document Review System

HyperDoc is an agentic document-processing system that extracts structured facts from documents, detects conflicting terms, generates a reviewable draft, and routes findings to a human reviewer.

The system is designed around a LangGraph execution pipeline with persisted checkpoints, provenance-aware extraction, conflict detection, and a React-based review interface.

---

## Overview

HyperDoc processes documents through the following flow:

```text
Document Upload
      ↓
Parsing & Chunking
      ↓
Fact Extraction
      ↓
Conflict Detection
      ↓
Draft Generation
      ↓
Human Review

The system preserves source provenance for extracted facts and records execution metrics such as stage timings and LLM token usage.

Supported Formats & Domain
Formats
PDF
DOCX
TXT
Intended Domain
Vendor contracts
Contract amendments
Invoices
Synthetic/public test data
Key Features
Document Processing
PDF, DOCX, and TXT ingestion
Document classification
Page-aware parsing where available
Chunking with overlap
Embedding generation
PostgreSQL + pgvector storage
Agentic Processing
LangGraph-based document agent
Persisted execution checkpoints
Resume support after interrupted execution
Concurrent run isolation
Extraction retry handling
Stage-level execution timing
Fact Extraction
Structured fact extraction using Groq LLM
Pydantic-validated extraction output
Source provenance for every extracted fact
Document and chunk identifiers normalized by application context
Protection against instructions embedded inside document data
Conflict Detection

The system groups extracted facts by normalized fact name and detects cases where the same fact has multiple distinct values.

Example:

Payment Terms: Net 30 days
Payment Terms: Net 60 days

This produces a conflict finding requiring human review.

Draft Generation

The agent generates a structured contract brief containing extracted facts and their source information.

Human Review

Reviewers can:

View detected conflicts
Inspect the generated draft
Inspect extracted facts
View source document/chunk provenance
Accept findings
Reject findings
Execution Metrics

Each agent run records:

Run ID
Current stage
Run status
Extraction attempts
Stage timings
Input tokens
Output tokens
Total LLM tokens
Total execution duration
Architecture
                         ┌─────────────────┐
                         │  React + Vite   │
                         │ Review Frontend │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │    FastAPI      │
                         │      API        │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │    LangGraph    │
                         │  Document Agent │
                         └────────┬────────┘
                                  │
              ┌───────────────────┼───────────────────┐
              ▼                   ▼                   ▼
        ┌───────────┐       ┌───────────┐       ┌───────────┐
        │  Ingest   │──────▶│  Extract  │──────▶│ Conflict  │
        │           │       │   Facts   │       │   Check   │
        └───────────┘       └───────────┘       └─────┬─────┘
                                                       │
                                                       ▼
                                                ┌───────────┐
                                                │   Draft   │
                                                └─────┬─────┘
                                                      │
                                                      ▼
                                                ┌───────────┐
                                                │  Review   │
                                                └───────────┘

                         ┌─────────────────┐
                         │ PostgreSQL +    │
                         │    pgvector     │
                         └─────────────────┘
Agent Pipeline

The LangGraph agent progresses through:

Ingest
  ↓
Extract
  ↓
Conflict Check
  ↓
Draft
  ↓
Review

Execution checkpoints are persisted so an interrupted run can resume from its last completed stage rather than unnecessarily starting over.

The agent also records timing information for each stage.

Example:

{
  "stage_timings": {
    "ingest": 0.0,
    "extract": 2.4041,
    "conflict_check": 0.0094,
    "draft": 0.0027,
    "review": 0.0
  }
}
LLM Usage

The extraction agent uses a Groq-hosted LLM.

LLM usage is captured from the model response metadata and returned as part of the agent result.

Example:

{
  "llm_usage": {
    "input_tokens": 265,
    "output_tokens": 299,
    "total_tokens": 564
  }
}

This makes model usage visible without requiring the frontend to estimate token consumption.

Provenance

Every extracted fact retains source information including:

Document ID
Chunk ID
Page number when available
Section when available

Example:

{
  "id": 230,
  "document_id": 72,
  "chunk_id": 60,
  "fact": "Vendor",
  "value": "Acme Supplies",
  "page_number": null,
  "section": null
}

Source metadata is normalized from application context rather than relying on identifiers generated by the LLM.

Prompt Injection Handling

Document content is treated strictly as data during fact extraction.

Instructions contained inside uploaded documents are explicitly treated as document content rather than agent instructions.

The test suite includes a prompt-injection case verifying this behavior.

API
Upload Document
POST /documents/upload

Accepts a PDF, DOCX, or TXT file.

Example response:

{
  "document_id": 72,
  "filename": "conflict.txt",
  "document_type": "unknown",
  "chunks": 1
}
Run Document Agent
POST /documents/agent/run

Request:

{
  "document_ids": [72]
}

The response contains the agent run information, extracted facts, findings, generated draft, stage timings, and LLM usage.

Get Findings
GET /findings/{document_id}

Returns findings detected for the specified document.

Review Finding
POST /findings/{finding_id}/review

Accept:

{
  "decision": "accepted"
}

Reject:

{
  "decision": "rejected"
}
Interactive API Documentation

When the backend is running:

http://127.0.0.1:8000/docs
Frontend

The frontend is implemented using React and Vite.

The review interface provides:

Document upload
Agent execution
Analysis summary
Run status
Extracted fact count
Finding count
Execution duration
LLM token usage
Pipeline stage timings
Extracted facts
Source provenance
Generated draft
Conflict findings
Accept / Reject review actions

Start the frontend:

cd frontend
npm install
npm run dev

Production build:

npm run build
Quickstart

Clone the repository:

git clone <this-repo>
cd hyperdoc

Create the environment file:

cp .env.example .env

Add the required Groq API key:

GROQ_API_KEY=your_key_here

Start PostgreSQL and pgvector:

docker compose up -d

Create the Python environment:

python -m venv .venv

Windows:

.venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt

Start the backend:

uvicorn app.main:app --reload

Health check:

curl http://127.0.0.1:8000/health

Start the frontend in a second terminal:

cd frontend
npm install
npm run dev
Tech Stack
Backend
Python 3.11
FastAPI
SQLAlchemy
PostgreSQL
pgvector
LangGraph
Groq
Pydantic
Frontend
React
Vite
React Markdown
CSS
Infrastructure
Docker
PostgreSQL
pgvector
Testing

Run the complete test suite:

python -m pytest -v

Current verified result:

21 passed

The test suite covers:

Checkpoint roundtrip
Chunk provenance
Concurrent agent isolation
Conflict detection
Database connectivity
Draft generation
Embedding dimensions
Fact persistence
Finding persistence
Agent graph execution
TXT ingestion
Kill/resume behavior
LLM connectivity
PDF parsing
DOCX parsing
Prompt injection handling
Checkpoint resume
Execution resume
Agent runner
Semantic search
Example Conflict

The sample conflict document contains:

Payment Terms: Net 30 days.

...

Amendment

Payment Terms: Net 60 days.

HyperDoc extracts both values and identifies them as conflicting terms.

The resulting finding is routed to the human review stage where the reviewer can accept or reject the finding.

Design Tradeoffs
Groq LLM

Groq is used for fast inference and straightforward development.

This was chosen as a cost and latency tradeoff rather than using a more expensive hosted model.

Simple Fact Grouping

Conflict detection currently groups extracted facts by normalized fact name and compares their distinct values.

This keeps the conflict-detection layer deterministic and easy to inspect.

Chunking

Documents are split into bounded chunks with overlap while preserving page and section metadata where available.

Human-in-the-Loop

The system deliberately stops at the review stage rather than automatically resolving detected conflicts.

This allows a human reviewer to make the final decision.

Current Status

HyperDoc currently supports the complete workflow:

Upload
  ↓
Parse
  ↓
Chunk
  ↓
Extract Facts
  ↓
Detect Conflicts
  ↓
Generate Draft
  ↓
Human Review
  ↓
Accept / Reject

The backend, agent pipeline, persistence layer, API, and React review interface are implemented and integrated.

