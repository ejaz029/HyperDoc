from app.db.database import SessionLocal
from app.db.models import Document, ExtractedFactModel
from app.services.draft import build_draft


def test_build_draft():
    db = SessionLocal()

    try:
        document = Document(
            filename="vendor_contract.txt",
            document_type="contract",
        )
        db.add(document)
        db.flush()

        fact = ExtractedFactModel(
            document_id=document.id,
            chunk_id=1,
            fact="Payment Terms",
            value="Net 30 days",
            page_number=2,
            section="Payment Terms",
        )
        db.add(fact)
        db.commit()

        draft = build_draft(db, document.id)

        assert "# Vendor Contract Brief" in draft
        assert "Net 30 days" in draft
        assert "Page 2" in draft
        assert "Chunk 1" in draft

    finally:
        db.rollback()
        db.close()