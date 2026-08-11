from app.db.database import SessionLocal
from app.db.models import Document, DocumentChunk, ExtractedFactModel
from app.services.conflicts import find_conflicts


def test_find_conflicts():
    db = SessionLocal()

    try:
        document = Document(
            filename="contract.txt",
            document_type="contract",
        )
        db.add(document)
        db.flush()

        chunk1 = DocumentChunk(
            document_id=document.id,
            chunk_index=0,
            content="Payment Terms: Net 30 days",
        )

        chunk2 = DocumentChunk(
            document_id=document.id,
            chunk_index=1,
            content="Payment Terms: Net 60 days",
        )

        db.add_all([chunk1, chunk2])
        db.flush()

        db.add_all(
            [
                ExtractedFactModel(
                    document_id=document.id,
                    chunk_id=chunk1.id,
                    fact="Payment Terms",
                    value="Net 30 days",
                ),
                ExtractedFactModel(
                    document_id=document.id,
                    chunk_id=chunk2.id,
                    fact="Payment Terms",
                    value="Net 60 days",
                ),
            ]
        )

        db.commit()

        conflicts = find_conflicts(
            db,
            document.id,
        )

        assert len(conflicts) == 1
        assert conflicts[0].fact == "payment terms"
        assert set(conflicts[0].values) == {
            "Net 30 days",
            "Net 60 days",
        }

    finally:
        db.rollback()
        db.close()