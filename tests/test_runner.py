from app.agent.runner import run_agent
from app.db.database import SessionLocal
from app.db.models import AgentRun


def test_run_agent():
    result = run_agent([1])

    assert result["current_stage"] == "review"
    assert result["status"] == "waiting_for_review"

    db = SessionLocal()

    try:
        run = db.query(AgentRun).order_by(AgentRun.id.desc()).first()

        assert run is not None
        assert run.status == "waiting_for_review"
        assert run.current_stage == "review"

    finally:
        db.close()