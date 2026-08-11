from app.db.database import SessionLocal
from app.db.models import Document, DocumentChunk
from app.services.extraction import (
    extract_facts,
    save_extracted_facts,
)


def test_save_extracted_facts():
    db = SessionLocal()

    try:
        document = Document(
            filename="vendor_contract.txt",
            document_type="contract",
        )
        db.add(document)
        db.flush()

        chunk = DocumentChunk(
            document_id=document.id,
            chunk_index=0,
            content=(
                "Vendor: Acme Supplies. "
                "Contract Value: $50,000. "
                "Payment Terms: Net 30 days."
            ),
            page_number=2,
            section="Payment Terms",
        )
        db.add(chunk)
        db.flush()

        result = extract_facts(
            document_id=document.id,
            chunk_id=chunk.id,
            content=chunk.content,
            page_number=chunk.page_number,
            section=chunk.section,
        )

        saved = save_extracted_facts(db, result)

        assert len(saved) > 0
        assert saved[0].document_id == document.id
        assert saved[0].chunk_id == chunk.id

    finally:
        db.rollback()
        db.close()