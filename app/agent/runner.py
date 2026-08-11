from app.agent.checkpoint import create_run, save_checkpoint
from app.agent.graph import build_graph
from app.db.database import SessionLocal


def run_agent(document_ids: list[int]) -> dict:
    db = SessionLocal()

    try:
        initial_state = {
            "document_ids": document_ids,
            "status": "pending",
        }

        run = create_run(db, initial_state)

        graph = build_graph()

        state = {
            **initial_state,
            "run_id": run.id,
        }

        result = graph.invoke(state)

        save_checkpoint(
            db,
            run.id,
            result,
            stage=result["current_stage"],
            status=result["status"],
        )

        return result

    finally:
        db.close()