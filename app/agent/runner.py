import time

from app.agent.checkpoint import create_run, save_checkpoint
from app.agent.graph import build_graph
from app.db.database import SessionLocal


def run_agent(
    document_ids: list[int],
    rules: list[str] | None = None,
) -> dict:
    db = SessionLocal()
    start_time = time.perf_counter()

    try:
        initial_state = {
            "document_ids": document_ids,
            "rules": rules or [],
            "status": "pending",
            "stage_timings": {},
            "llm_usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        }

        run = create_run(db, initial_state)

        graph = build_graph()

        state = {
            **initial_state,
            "run_id": run.id,
        }

        result = graph.invoke(state)

        result["total_duration_seconds"] = round(
            time.perf_counter() - start_time,
            3,
        )

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