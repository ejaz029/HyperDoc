from app.agent.checkpoint import (
    create_run,
    load_checkpoint,
    save_checkpoint,
)
from app.db.database import SessionLocal


def test_checkpoint_roundtrip():
    db = SessionLocal()

    try:
        state = {
            "document_ids": [1],
            "current_stage": "ingest",
            "status": "running",
        }

        run = create_run(db, state)

        updated_state = {
            **state,
            "current_stage": "extract",
            "extracted_fact_ids": [10, 11],
        }

        save_checkpoint(
            db,
            run.id,
            updated_state,
            stage="extract",
        )

        loaded = load_checkpoint(db, run.id)

        assert loaded["current_stage"] == "extract"
        assert loaded["extracted_fact_ids"] == [10, 11]

    finally:
        db.close()