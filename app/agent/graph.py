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


def checkpoint_node(stage: str, state: AgentState) -> AgentState:
    db = SessionLocal()

    try:
        updated = {
            **state,
            "current_stage": stage,
            "status": "completed",
        }

        save_checkpoint(
            db,
            state["run_id"],
            updated,
            stage=stage,
            status="completed",
        )

        return updated

    finally:
        db.close()


def ingest_node(state: AgentState) -> AgentState:
    return checkpoint_node("ingest", state)


def extract_node(state: AgentState) -> AgentState:
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

        updated = {
            **state,
            "current_stage": "extract",
            "status": "completed",
            "extracted_fact_ids": extracted_fact_ids,
            "extraction_attempts": attempts,
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

        updated = {
            **state,
            "current_stage": "conflict_check",
            "status": "completed",
            "finding_ids": finding_ids,
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
    return checkpoint_node("draft", state)


def review_node(state: AgentState) -> AgentState:
    db = SessionLocal()

    try:
        updated = {
            **state,
            "current_stage": "review",
            "status": "waiting_for_review",
        }

        save_checkpoint(
            db,
            state["run_id"],
            updated,
            stage="review",
            status="waiting_for_review",
        )

        return updated

    finally:
        db.close()


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