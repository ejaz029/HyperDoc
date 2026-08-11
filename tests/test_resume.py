from app.agent.checkpoint import create_run, save_checkpoint
from app.agent.graph import STAGES
from app.db.database import SessionLocal


def test_resume_checkpoint():
    db = SessionLocal()

    try:
        state = {
            "document_ids": [1],
            "current_stage": "extract",
            "status": "completed",
        }

        run = create_run(db, state)

        save_checkpoint(
            db,
            run.id,
            state,
            stage="extract",
            status="completed",
        )

        assert state["current_stage"] == "extract"
        assert STAGES.index("extract") == 1

    finally:
        db.close()