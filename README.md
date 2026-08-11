# HyperDoc
## Agentic Document Review System

### Overview
HyperDoc is an agentic document-processing system that extracts structured facts from documents, detects conflicting terms, and routes findings to a human for review.

### Formats & Domain Accepted
- Formats: PDF, DOCX, TXT
- Domain: vendor contracts, amendments, invoices (synthetic/public test data only)

### Quickstart
```bash
git clone <this-repo>
cd hyperdoc
cp .env.example .env
# add your GROQ_API_KEY to .env

docker compose up -d          # Postgres + pgvector

python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt

uvicorn app.main:app --reload
```
Health check: `curl http://127.0.0.1:8000/health`

Frontend:
```bash
cd frontend
npm install
npm run dev
```
Production build:
```bash
npm run build
```

### Architecture

Document Upload
-> Parsing & Chunking
-> Fact Extraction (Groq LLM)
-> Conflict Detection
-> Finding Creation
-> Human Review


### Tech Stack
- Python 3.11
- FastAPI
- PostgreSQL + pgvector
- SQLAlchemy
- LangGraph
- Groq LLM
- React + Vite
- Docker

### API

**Upload Document**
`POST /documents/upload`
Accepts a document, creates the document record and chunks.

**Get Findings**
`GET /findings/{document_id}`
Returns conflicts detected for a document.

**Review Finding**
`POST /findings/{finding_id}/review`
```json
{ "decision": "accepted" }
```
or
```json
{ "decision": "rejected" }
```

Full interactive docs when the backend is running: `http://127.0.0.1:8000/docs`

### Agent Pipeline
The LangGraph agent progresses through: **Ingest -> Extract -> Conflict Check -> Draft -> Review**.
Checkpoints are persisted at each stage, so a run can resume from its last completed stage after a crash or manual kill.

**Verify resumability:**
```bash
# start a run, kill it mid-way (Ctrl+C or kill the process), then restart —
# it resumes from the last persisted checkpoint instead of re-processing from scratch
```

### Human Review
AI-detected conflicts are displayed in the React frontend. Reviewers accept or reject individual findings; rejecting one does not discard the rest.

### Provenance
Extracted facts retain their document and chunk provenance. Source metadata is normalized from the application context rather than relying on LLM-generated identifiers — this is what keeps every claim traceable to an exact source location, not just plausible-looking.

### Testing
```bash
python -m pytest -v
```
Current result: 19/19 tests passing, no live API key required.

### Known Tradeoffs
- Fact extraction uses Groq (fast, free-tier friendly) rather than OpenAI — logged here as a deliberate cost/latency choice, not an oversight.
- (Add any other deviations here — chunking method, classifier approach, etc.)

### Example Conflict
`data/sample/conflict.txt` contains contradictory payment terms — Net 30 days vs Net 60 days. HyperDoc detects the conflict and creates a pending finding for human review.