import time

from langgraph.graph import END, START, StateGraph

from app.agent.checkpoint import save_checkpoint
from app.agent.state import AgentState
from app.db.database import SessionLocal


STAGES = [
    "ingest",
    "extract",
    "conflict_check",
    "draft",
    "review",
]


def save_stage_checkpoint(
    stage: str,
    state: AgentState,
    started_at: float,
    status: str = "completed",
) -> AgentState:
    db = SessionLocal()

    try:
        elapsed = round(time.perf_counter() - started_at, 4)

        timings = {
            **state.get("stage_timings", {}),
            stage: elapsed,
        }

        updated = {
            **state,
            "current_stage": stage,
            "status": status,
            "stage_timings": timings,
        }

        save_checkpoint(
            db,
            state["run_id"],
            updated,
            stage=stage,
            status=status,
        )

        return updated

    finally:
        db.close()


def ingest_node(state: AgentState) -> AgentState:
    started_at = time.perf_counter()
    return save_stage_checkpoint(
        "ingest",
        state,
        started_at,
    )


def extract_node(state: AgentState) -> AgentState:
    started_at = time.perf_counter()

    from app.db.models import DocumentChunk
    from app.services.extraction import (
        extract_facts,
        save_extracted_facts,
    )

    db = SessionLocal()

    try:
        document_ids = state.get("document_ids", [])
        extracted_fact_ids = []
        attempts = state.get("extraction_attempts", 0) + 1

        llm_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

        for document_id in document_ids:
            chunks = (
                db.query(DocumentChunk)
                .filter(DocumentChunk.document_id == document_id)
                .order_by(DocumentChunk.chunk_index)
                .all()
            )

            for chunk in chunks:
                result = extract_facts(
                    document_id=document_id,
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

        elapsed = round(
            time.perf_counter() - started_at,
            4,
        )

        updated = {
            **state,
            "current_stage": "extract",
            "status": "completed",
            "extracted_fact_ids": extracted_fact_ids,
            "extraction_attempts": attempts,
            "llm_usage": llm_usage,
            "stage_timings": {
                **state.get("stage_timings", {}),
                "extract": elapsed,
            },
        }

        save_checkpoint(
            db,
            state["run_id"],
            updated,
            stage="extract",
            status="completed",
        )

        return updated

    finally:
        db.close()


def route_after_extract(state: AgentState):
    fact_ids = state.get("extracted_fact_ids", [])
    attempts = state.get("extraction_attempts", 0)

    if fact_ids:
        return "conflict_check"

    if attempts < 2:
        return "retry_extract"

    return "escalate_review"


def conflict_check_node(state: AgentState) -> AgentState:
    started_at = time.perf_counter()

    from app.services.conflicts import find_conflicts
    from app.services.findings import save_conflicts

    db = SessionLocal()

    try:
        document_ids = state.get("document_ids", [])
        finding_ids = []

        for document_id in document_ids:
            conflicts = find_conflicts(
                db,
                document_id,
            )

            findings = save_conflicts(
                db,
                document_id,
                conflicts,
            )

            finding_ids.extend(
                finding.id
                for finding in findings
            )

        elapsed = round(
            time.perf_counter() - started_at,
            4,
        )

        updated = {
            **state,
            "current_stage": "conflict_check",
            "status": "completed",
            "finding_ids": finding_ids,
            "stage_timings": {
                **state.get("stage_timings", {}),
                "conflict_check": elapsed,
            },
        }

        save_checkpoint(
            db,
            state["run_id"],
            updated,
            stage="conflict_check",
            status="completed",
        )

        return updated

    finally:
        db.close()


def draft_node(state: AgentState) -> AgentState:
    started_at = time.perf_counter()

    return save_stage_checkpoint(
        "draft",
        state,
        started_at,
    )


def review_node(state: AgentState) -> AgentState:
    started_at = time.perf_counter()

    return save_stage_checkpoint(
        "review",
        state,
        started_at,
        status="waiting_for_review",
    )


def route_start(state: AgentState):
    stage = state.get("current_stage")

    if stage == "ingest":
        return "extract"

    if stage == "extract":
        return "conflict_check"

    if stage == "conflict_check":
        return "draft"

    if stage == "draft":
        return "review"

    return "ingest"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node("ingest", ingest_node)
    graph.add_node("extract", extract_node)
    graph.add_node("conflict_check", conflict_check_node)
    graph.add_node("draft", draft_node)
    graph.add_node("review", review_node)

    graph.add_conditional_edges(
        START,
        route_start,
        {
            "ingest": "ingest",
            "extract": "extract",
            "conflict_check": "conflict_check",
            "draft": "draft",
            "review": "review",
        },
    )

    graph.add_edge("ingest", "extract")

    graph.add_conditional_edges(
        "extract",
        route_after_extract,
        {
            "conflict_check": "conflict_check",
            "retry_extract": "extract",
            "escalate_review": "review",
        },
    )

    graph.add_edge("conflict_check", "draft")
    graph.add_edge("draft", "review")
    graph.add_edge("review", END)

    return graph.compile()