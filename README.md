# HyperDoc

## Agentic Document Review System

HyperDoc is an agentic document-processing system that extracts structured facts from documents, detects conflicting terms, generates a reviewable draft, and routes findings to a human reviewer.

The system is built around a LangGraph execution pipeline with persisted checkpoints, provenance-aware extraction, conflict detection, incremental document updates, and a React-based review interface.

---

## Supported Formats & Domain

### Formats

- PDF
- DOCX
- TXT

### Intended Domain

- Vendor contracts
- Contract amendments
- Invoices
- Synthetic/public test data

---

## Core Workflow

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
Branching after extraction
Fact Extraction
Structured fact extraction using Groq LLM
Pydantic-validated extraction output
Source provenance for every extracted fact
Document and chunk identifiers normalized by application context
Document content treated as data rather than instructions
Conflict Detection

The system groups extracted facts by normalized fact name and detects cases where the same fact has multiple distinct values.

Example:

Payment Terms: Net 30 days
Payment Terms: Net 60 days

This produces a conflict finding requiring human review.

Rules / Checklist Examination

The agent can evaluate uploaded documents against explicit review rules.

Example:

Payment terms must be Net 30 days.
The contract must identify the vendor.

Rule violations become reviewable findings.

Never-Bluff Grounding

HyperDoc includes a deterministic source-grounding path for unsupported claims.

When sufficiently strong source evidence cannot be found, the system explicitly returns:

Not supported by the provided documents.

This behavior is covered by an automated test.

Incremental Updates

A newly added document can be processed independently instead of re-extracting the existing document set.

Existing Documents
       ↓
New Document
       ↓
Extract ONLY New Document
       ↓
Compare Against Existing Facts
       ↓
Create New Findings
       ↓
Generate Incremental Update
       ↓
Human Review
Watched Location

HyperDoc can watch a folder for new PDF, DOCX, and TXT files.

When a new file appears:

New File
   ↓
Ingest
   ↓
Incremental Agent
   ↓
Extract New Facts
   ↓
Compare With Existing Facts
   ↓
Create Findings
   ↓
Incremental Draft
   ↓
Human Review

Start the watcher through:

POST /documents/watch/start

Example:

{
  "folder": "data/watch",
  "existing_document_ids": [72],
  "rules": [
    "Payment terms must be Net 30 days."
  ]
}
Architecture
                         ┌──────────────────────┐
                         │     React + Vite      │
                         │   Review Frontend     │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │       FastAPI        │
                         │         API          │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │      LangGraph       │
                         │    Document Agent    │
                         └──────────┬───────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              ▼                     ▼                     ▼
          Ingest                 Extract            Conflict Check
              │                     │                     │
              └─────────────────────┼─────────────────────┘
                                    ▼
                              Draft Generation
                                    │
                                    ▼
                              Human Review

                         ┌──────────────────────┐
                         │ PostgreSQL + pgvector│
                         └──────────────────────┘
Agent Pipeline

The normal LangGraph agent progresses through:

Ingest
  ↓
Extract
  ↓
Conflict Check
  ↓
Draft
  ↓
Review

After extraction, the graph can branch to retry extraction when no facts are produced.

Execution checkpoints are persisted so an interrupted run can resume from its last completed stage rather than unnecessarily starting over.

Each stage records its execution time.

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

LLM usage is captured from model response metadata and returned as part of the agent result.

Example:

{
  "llm_usage": {
    "input_tokens": 265,
    "output_tokens": 299,
    "total_tokens": 564
  }
}
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

Instructions contained inside uploaded documents are treated as document content rather than agent instructions.

The test suite includes a prompt-injection case verifying this behavior.

API
Upload Document
POST /documents/upload

Accepts:

PDF
DOCX
TXT

Example response:

{
  "document_id": 72,
  "filename": "conflict.txt",
  "document_type": "unknown",
  "chunks": 1
}
Run Document Agent
POST /documents/agent/run

Example request:

{
  "document_ids": [72],
  "rules": [
    "Payment terms must be Net 30 days."
  ]
}

The response contains:

Agent run information
Extracted facts
Findings
Generated draft
Stage timings
LLM usage
Rule findings
Run Incremental Agent
POST /documents/agent/run-incremental

Example:

{
  "existing_document_ids": [72],
  "new_document_id": 73,
  "rules": [
    "Payment terms must be Net 30 days."
  ]
}

The incremental run extracts only the new document and compares its facts with existing documents.

Start Document Watcher
POST /documents/watch/start

Example:

{
  "folder": "data/watch",
  "existing_document_ids": [72],
  "rules": [
    "Payment terms must be Net 30 days."
  ]
}
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

Each finding is reviewed independently.

Interactive API Documentation

When the backend is running:

http://127.0.0.1:8000/docs
Frontend

The frontend uses React and Vite.

The review interface provides:

Document upload
Review rules/checklist
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
Rule findings
Accept / Reject review actions

Start the frontend:

cd frontend
npm install
npm run dev

Production build:

npm run build
Quickstart
1. Clone
git clone <this-repo>
cd hyperdoc
2. Create environment file

Copy the example:

cp .env.example .env

On Windows PowerShell:

Copy-Item .env.example .env

Set:

DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/doctask
GROQ_API_KEY=your_groq_api_key_here
3. Start PostgreSQL + pgvector
docker compose up -d
4. Create Python environment
python -m venv .venv

Windows:

.venv\Scripts\activate
5. Install dependencies
pip install -r requirements.txt
6. Create database tables
python -m app.db.init_db

This step is required on a clean database.

7. Start backend
uvicorn app.main:app --reload

Health check:

http://127.0.0.1:8000/health

Expected response:

{
  "status": "ok"
}
8. Start frontend

Open a second terminal:

cd frontend
npm install
npm run dev
Environment Variables

.env.example contains:

DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/doctask
GROQ_API_KEY=your_groq_api_key_here

A valid Groq API key is required for live LLM extraction.

Testing

Run:

python -m pytest -v

The test suite is designed to cover:

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
PDF parsing
DOCX parsing
Prompt injection handling
Checkpoint resume
Execution resume
Agent runner
Semantic search
Unsupported-claim grounding
Important

The live LLM connectivity test requires a working Groq API configuration.

Therefore, a completely offline environment should not be described as having every test pass without credentials.

Example Conflict

The sample conflict document contains:

Payment Terms: Net 30 days.

...

Amendment

Payment Terms: Net 60 days.

HyperDoc extracts both values and identifies them as conflicting terms.

The resulting finding is routed to human review where the reviewer can accept or reject it.

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

Incremental Processing

New documents can be analyzed independently and compared against existing extracted facts rather than forcing a complete re-analysis.

Current Status

HyperDoc supports the complete implemented workflow:

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
Rule Check
  ↓
Generate Draft
  ↓
Human Review
  ↓
Accept / Reject

It also supports:

New Document
      ↓
Watched Folder
      ↓
Incremental Extraction
      ↓
Existing Fact Comparison
      ↓
New Findings
      ↓
Incremental Draft
      ↓
Human Review

The backend, agent pipeline, persistence layer, API, incremental processing, watched-folder processing, and React review interface are implemented and integrated.