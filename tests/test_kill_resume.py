from app.agent.checkpoint import create_run, save_checkpoint
from app.agent.resume import resume_agent
from app.db.database import SessionLocal


def test_kill_and_resume():
    db = SessionLocal()

    try:
        state = {
            "run_id": None,
            "document_ids": [1],
            "current_stage": "extract",
            "status": "completed",
        }

        run = create_run(db, state)

        state["run_id"] = run.id

        save_checkpoint(
            db,
            run.id,
            state,
            stage="extract",
            status="completed",
        )

        run_id = run.id

    finally:
        db.close()

    # Simulate process death here.
    del state

    # New execution resumes the persisted run.
    result = resume_agent(run_id)

    assert result["current_stage"] == "review"
    assert result["status"] == "waiting_for_review"