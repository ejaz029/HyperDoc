from app.db.database import SessionLocal
from app.db.models import Document
from app.ingestion.service import ingest_document


def test_ingest_txt():
    db = SessionLocal()

    try:
        document = ingest_document(
            db=db,
            file_path="data/sample/test.txt",
            filename="vendor_contract.txt",
        )

        assert document.id is not None
        assert document.document_type == "contract"
        assert len(document.chunks) == 1
        assert len(document.chunks[0].embedding) == 384
        chunk = document.chunks[0]

        assert "Acme Supplies" in chunk.content
        assert chunk.chunk_index == 0

    finally:
        db.close()