import json

from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import (
    AgentRun,
    Document,
    DocumentChunk,
    ExtractedFactModel,
    Finding,
)


router = APIRouter(
    prefix="/changes",
    tags=["changes"],
)


@router.get("/{document_id}")
def get_document_changes(
    document_id: int,
):
    db = SessionLocal()

    try:
        document = db.get(
            Document,
            document_id,
        )

        if document is None:
            raise HTTPException(
                status_code=404,
                detail="Document not found",
            )

        facts = list(
            db.scalars(
                select(
                    ExtractedFactModel
                )
                .where(
                    ExtractedFactModel.document_id
                    == document_id
                )
                .order_by(
                    ExtractedFactModel.id
                )
            )
        )

        findings = list(
            db.scalars(
                select(Finding)
                .where(
                    Finding.document_id
                    == document_id
                )
                .order_by(
                    Finding.id
                )
            )
        )

        chunks = list(
            db.scalars(
                select(DocumentChunk)
                .where(
                    DocumentChunk.document_id
                    == document_id
                )
                .order_by(
                    DocumentChunk.chunk_index
                )
            )
        )

        runs = list(
            db.scalars(
                select(AgentRun)
                .order_by(
                    AgentRun.id.desc()
                )
            )
        )

        related_runs = []

        for run in runs:
            try:
                state = json.loads(
                    run.state_json
                )
            except (
                TypeError,
                ValueError,
            ):
                continue

            document_ids = state.get(
                "document_ids",
                [],
            )

            new_document_id = state.get(
                "new_document_id"
            )

            if (
                document_id in document_ids
                or new_document_id == document_id
            ):
                related_runs.append(
                    {
                        "run_id": run.id,
                        "status": run.status,
                        "current_stage": (
                            run.current_stage
                        ),
                        "created_at": (
                            run.created_at.isoformat()
                            if run.created_at
                            else None
                        ),
                        "updated_at": (
                            run.updated_at.isoformat()
                            if run.updated_at
                            else None
                        ),
                        "incremental": (
                            new_document_id
                            == document_id
                        ),
                    }
                )

        source_chunks = {
            chunk.id: {
                "chunk_id": chunk.id,
                "document_id": chunk.document_id,
                "page_number": chunk.page_number,
                "section": chunk.section,
            }
            for chunk in chunks
        }

        return {
            "document": {
                "id": document.id,
                "filename": document.filename,
                "document_type": (
                    document.document_type
                ),
                "created_at": (
                    document.created_at.isoformat()
                    if document.created_at
                    else None
                ),
            },
            "summary": {
                "facts_added": len(facts),
                "findings_created": len(findings),
                "chunks_available": len(chunks),
            },
            "changes": [
                {
                    "fact_id": fact.id,
                    "fact": fact.fact,
                    "value": fact.value,
                    "source": {
                        "document_id": fact.document_id,
                        "chunk_id": fact.chunk_id,
                        "page_number": fact.page_number,
                        "section": fact.section,
                    },
                    "changed_at": (
                        document.created_at.isoformat()
                        if document.created_at
                        else None
                    ),
                }
                for fact in facts
            ],
            "findings": [
                {
                    "finding_id": finding.id,
                    "type": finding.finding_type,
                    "description": finding.description,
                    "status": finding.status,
                    "fact_ids": finding.fact_ids,
                    "created_at": (
                        finding.created_at.isoformat()
                        if finding.created_at
                        else None
                    ),
                }
                for finding in findings
            ],
            "sources": list(
                source_chunks.values()
            ),
            "related_runs": related_runs,
        }

    finally:
        db.close()