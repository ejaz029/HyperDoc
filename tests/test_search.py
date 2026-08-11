from app.db.database import SessionLocal
from app.services.search import search_chunks


def test_semantic_search():
    db = SessionLocal()

    try:
        results = search_chunks(
            db,
            "What are the vendor payment terms?",
            limit=3,
        )

        assert len(results) > 0
        assert any("Payment Terms" in result.content for result in results)

    finally:
        db.close()