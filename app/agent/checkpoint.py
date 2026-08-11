import json

from sqlalchemy.orm import Session

from app.db.models import AgentRun


def create_run(
    db: Session,
    state: dict,
) -> AgentRun:
    run = AgentRun(
        status="running",
        current_stage="start",
        state_json=json.dumps(state),
    )

    db.add(run)
    db.commit()
    db.refresh(run)

    return run


def save_checkpoint(
    db: Session,
    run_id: int,
    state: dict,
    stage: str,
    status: str = "running",
) -> AgentRun:
    run = db.get(AgentRun, run_id)

    if run is None:
        raise ValueError(f"Run {run_id} not found")

    run.current_stage = stage
    run.status = status
    run.state_json = json.dumps(state)

    db.commit()
    db.refresh(run)

    return run


def load_checkpoint(
    db: Session,
    run_id: int,
) -> dict:
    run = db.get(AgentRun, run_id)

    if run is None:
        raise ValueError(f"Run {run_id} not found")

    return json.loads(run.state_json)