from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.ingestion.service import ingest_document

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = Path("data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_document(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    extension = Path(file.filename or "").suffix.lower()

    if extension not in {".pdf", ".docx", ".txt"}:
        return {"error": f"Unsupported file type: {extension}"}

    filename = file.filename or "document"
    stored_name = f"{uuid4()}_{filename}"
    file_path = UPLOAD_DIR / stored_name

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