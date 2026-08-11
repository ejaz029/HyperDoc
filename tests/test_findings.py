from app.db.database import SessionLocal
from app.db.models import Document
from app.services.conflicts import ConflictFinding
from app.services.findings import save_conflicts


def test_save_conflicts():
    db = SessionLocal()

    try:
        document = Document(
            filename="contract.txt",
            document_type="contract",
        )
        db.add(document)
        db.flush()

        conflicts = [
            ConflictFinding(
                fact="payment terms",
                values=["Net 30 days", "Net 60 days"],
                fact_ids=[1, 2],
            )
        ]

        findings = save_conflicts(
            db,
            document.id,
            conflicts,
        )

        assert len(findings) == 1
        assert findings[0].document_id == document.id
        assert findings[0].finding_type == "conflict"
        assert findings[0].status == "pending"
        assert findings[0].fact_ids == "[1, 2]"

    finally:
        db.rollback()
        db.close()