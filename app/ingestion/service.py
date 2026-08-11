from pathlib import Path

from sqlalchemy.orm import Session

from app.db.models import Document, DocumentChunk
from app.ingestion.chunker import chunk_pages
from app.ingestion.parser import parse_document
from app.services.embeddings import embed_text

def classify_document(filename: str) -> str:
    name = Path(filename).name.lower()

    if "invoice" in name:
        return "invoice"

    if "amendment" in name or "addendum" in name:
        return "amendment"

    if "contract" in name or "agreement" in name:
        return "contract"

    return "unknown"


def ingest_document(
    db: Session,
    file_path: str,
    filename: str,
) -> Document:
    pages = parse_document(file_path)

    document = Document(
        filename=filename,
        document_type=classify_document(filename),
    )

    db.add(document)
    db.flush()

    chunks = chunk_pages(pages)

    for chunk in chunks:
        db_chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            page_number=chunk.page_number,
            section=chunk.section,
            embedding=embed_text(chunk.content),
        )
        db.add(db_chunk)

    db.commit()
    db.refresh(document)

    return document