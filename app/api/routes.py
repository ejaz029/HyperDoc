from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.agent.runner import (
    run_agent,
    run_incremental_agent,
)
from app.db.database import get_db
from app.db.models import ExtractedFactModel
from app.ingestion.service import ingest_document


router = APIRouter(
    prefix="/documents",
    tags=["documents"],
)

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


class AgentRunRequest(BaseModel):
    document_ids: list[int] = Field(
        min_length=1
    )

    rules: list[str] = Field(
        default_factory=list
    )


class IncrementalAgentRunRequest(BaseModel):
    existing_document_ids: list[int] = Field(
        default_factory=list
    )

    new_document_id: int

    rules: list[str] = Field(
        default_factory=list
    )


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    extension = Path(
        file.filename or ""
    ).suffix.lower()

    if extension not in {
        ".pdf",
        ".docx",
        ".txt",
    }:
        return {
            "error": (
                f"Unsupported file type: "
                f"{extension}"
            )
        }

    filename = (
        file.filename or "document"
    )

    stored_name = (
        f"{uuid4()}_{filename}"
    )

    file_path = (
        UPLOAD_DIR / stored_name
    )

    content = await file.read()
    file_path.write_bytes(content)

    document = ingest_document(
        db=db,
        file_path=str(file_path),
        filename=filename,
    )

    return {
        "document_id": document.id,
        "filename": document.filename,
        "document_type": document.document_type,
        "chunks": len(document.chunks),
    }


@router.post("/agent/run")
def run_document_agent(
    request: AgentRunRequest,
    db: Session = Depends(get_db),
):
    result = run_agent(
        document_ids=request.document_ids,
        rules=request.rules,
    )

    extracted_facts = list(
        db.scalars(
            select(ExtractedFactModel)
            .where(
                ExtractedFactModel.id.in_(
                    result.get(
                        "extracted_fact_ids",
                        [],
                    )
                )
            )
            .order_by(
                ExtractedFactModel.id
            )
        )
    )

    result["extracted_facts"] = [
        {
            "id": fact.id,
            "document_id": fact.document_id,
            "chunk_id": fact.chunk_id,
            "fact": fact.fact,
            "value": fact.value,
            "page_number": fact.page_number,
            "section": fact.section,
        }
        for fact in extracted_facts
    ]

    return result


@router.post("/agent/run-incremental")
def run_incremental_document_agent(
    request: IncrementalAgentRunRequest,
    db: Session = Depends(get_db),
):
    result = run_incremental_agent(
        existing_document_ids=(
            request.existing_document_ids
        ),
        new_document_id=request.new_document_id,
        rules=request.rules,
    )

    extracted_facts = list(
        db.scalars(
            select(ExtractedFactModel)
            .where(
                ExtractedFactModel.id.in_(
                    result.get(
                        "extracted_fact_ids",
                        [],
                    )
                )
            )
            .order_by(
                ExtractedFactModel.id
            )
        )
    )

    result["extracted_facts"] = [
        {
            "id": fact.id,
            "document_id": fact.document_id,
            "chunk_id": fact.chunk_id,
            "fact": fact.fact,
            "value": fact.value,
            "page_number": fact.page_number,
            "section": fact.section,
        }
        for fact in extracted_facts
    ]

    return result