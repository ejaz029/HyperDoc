from app.db.database import SessionLocal
from app.services.search import answer_grounded_claim


def test_unsupported_claim_is_explicitly_rejected():
    db = SessionLocal()

    try:
        result = answer_grounded_claim(
            db,
            "What is the employee's annual vacation allowance?",
        )

        assert result["supported"] is False
        assert (
            result["answer"]
            == "Not supported by the provided documents."
        )
        assert result["sources"] == []

    finally:
        db.close()