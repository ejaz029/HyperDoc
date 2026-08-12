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


def run_incremental_agent(
    existing_document_ids: list[int],
    new_document_id: int,
    rules: list[str] | None = None,
) -> dict:
    """
    Process only a newly added document and compare it
    against the existing document pile.

    Existing documents are not re-extracted.
    Existing facts are not deleted.
    Existing findings are not rebuilt.
    """

    from app.db.models import DocumentChunk
    from app.services.conflicts import (
        find_incremental_conflicts,
    )
    from app.services.draft import (
        build_incremental_update,
    )
    from app.services.extraction import (
        extract_facts,
        save_extracted_facts,
    )
    from app.services.findings import save_conflicts

    db = SessionLocal()
    start_time = time.perf_counter()

    try:
        document_ids = [
            *existing_document_ids,
            new_document_id,
        ]

        initial_state = {
            "document_ids": document_ids,
            "new_document_id": new_document_id,
            "existing_document_ids": existing_document_ids,
            "rules": rules or [],
            "status": "pending",
            "current_stage": "ingest",
            "stage_timings": {},
            "extracted_fact_ids": [],
            "finding_ids": [],
            "rule_finding_ids": [],
            "llm_usage": {
                "input_tokens": 0,
                "output_tokens": 0,
                "total_tokens": 0,
            },
        }

        run = create_run(
            db,
            initial_state,
        )

        run_id = run.id

        # -------------------------------------------------
        # INGEST CHECKPOINT
        # -------------------------------------------------

        ingest_started = time.perf_counter()

        state = {
            **initial_state,
            "run_id": run_id,
            "current_stage": "ingest",
            "status": "completed",
            "stage_timings": {
                "ingest": round(
                    time.perf_counter()
                    - ingest_started,
                    4,
                ),
            },
        }

        save_checkpoint(
            db,
            run_id,
            state,
            stage="ingest",
            status="completed",
        )

        # -------------------------------------------------
        # EXTRACT ONLY THE NEW DOCUMENT
        # -------------------------------------------------

        extract_started = time.perf_counter()

        extracted_fact_ids = []

        llm_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

        chunks = (
            db.query(DocumentChunk)
            .filter(
                DocumentChunk.document_id
                == new_document_id
            )
            .order_by(
                DocumentChunk.chunk_index
            )
            .all()
        )

        for chunk in chunks:
            result = extract_facts(
                document_id=new_document_id,
                chunk_id=chunk.id,
                content=chunk.content,
                page_number=chunk.page_number,
                section=chunk.section,
            )

            saved = save_extracted_facts(
                db,
                result,
            )

            extracted_fact_ids.extend(
                fact.id
                for fact in saved
            )

            usage = result.usage

            llm_usage["input_tokens"] += usage.get(
                "input_tokens",
                0,
            )

            llm_usage["output_tokens"] += usage.get(
                "output_tokens",
                0,
            )

            llm_usage["total_tokens"] += usage.get(
                "total_tokens",
                0,
            )

        state = {
            **state,
            "current_stage": "extract",
            "status": "completed",
            "extracted_fact_ids": extracted_fact_ids,
            "extraction_attempts": 1,
            "llm_usage": llm_usage,
            "stage_timings": {
                **state.get(
                    "stage_timings",
                    {},
                ),
                "extract": round(
                    time.perf_counter()
                    - extract_started,
                    4,
                ),
            },
        }

        save_checkpoint(
            db,
            run_id,
            state,
            stage="extract",
            status="completed",
        )

        # -------------------------------------------------
        # INCREMENTAL CONFLICT CHECK
        # -------------------------------------------------

        conflict_started = time.perf_counter()

        conflicts = find_incremental_conflicts(
            db,
            new_document_id,
        )

        findings = save_conflicts(
            db,
            new_document_id,
            conflicts,
        )

        finding_ids = [
            finding.id
            for finding in findings
        ]

        state = {
            **state,
            "current_stage": "conflict_check",
            "status": "completed",
            "finding_ids": finding_ids,
            "stage_timings": {
                **state.get(
                    "stage_timings",
                    {},
                ),
                "conflict_check": round(
                    time.perf_counter()
                    - conflict_started,
                    4,
                ),
            },
        }

        save_checkpoint(
            db,
            run_id,
            state,
            stage="conflict_check",
            status="completed",
        )

        # -------------------------------------------------
        # INCREMENTAL DRAFT
        # -------------------------------------------------

        draft_started = time.perf_counter()

        draft = build_incremental_update(
            db,
            new_document_id,
        )

        state = {
            **state,
            "current_stage": "draft",
            "status": "completed",
            "draft": draft,
            "stage_timings": {
                **state.get(
                    "stage_timings",
                    {},
                ),
                "draft": round(
                    time.perf_counter()
                    - draft_started,
                    4,
                ),
            },
        }

        save_checkpoint(
            db,
            run_id,
            state,
            stage="draft",
            status="completed",
        )

        # -------------------------------------------------
        # HUMAN REVIEW
        # -------------------------------------------------

        review_started = time.perf_counter()

        state = {
            **state,
            "current_stage": "review",
            "status": "waiting_for_review",
            "stage_timings": {
                **state.get(
                    "stage_timings",
                    {},
                ),
                "review": round(
                    time.perf_counter()
                    - review_started,
                    4,
                ),
            },
        }

        state["total_duration_seconds"] = round(
            time.perf_counter()
            - start_time,
            3,
        )

        save_checkpoint(
            db,
            run_id,
            state,
            stage="review",
            status="waiting_for_review",
        )

        return state

    finally:
        db.close()