from app.agent.checkpoint import load_checkpoint
from app.agent.graph import build_graph
from app.db.database import SessionLocal


def resume_agent(run_id: int) -> dict:
    db = SessionLocal()

    try:
        state = load_checkpoint(db, run_id)
    finally:
        db.close()

    state["run_id"] = run_id

    if state.get("current_stage") == "review":
        return state

    graph = build_graph()

    return graph.invoke(state)