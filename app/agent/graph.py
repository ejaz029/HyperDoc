import re
import time

from langgraph.graph import END, START, StateGraph

from app.agent.checkpoint import save_checkpoint
from app.agent.state import AgentState
from app.db.database import SessionLocal


STAGES = [
    "ingest",
    "extract",
    "conflict_check",
    "rule_check",
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
        elapsed = round(
            time.perf_counter() - started_at,
            4,
        )

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

        attempts = (
            state.get("extraction_attempts", 0) + 1
        )

        llm_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "total_tokens": 0,
        }

        for document_id in document_ids:
            chunks = (
                db.query(DocumentChunk)
                .filter(
                    DocumentChunk.document_id
                    == document_id
                )
                .order_by(
                    DocumentChunk.chunk_index
                )
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
    fact_ids = state.get(
        "extracted_fact_ids",
        [],
    )

    attempts = state.get(
        "extraction_attempts",
        0,
    )

    if fact_ids:
        return "conflict_check"

    if attempts < 2:
        return "retry_extract"

    return "escalate_review"


def conflict_check_node(
    state: AgentState,
) -> AgentState:
    started_at = time.perf_counter()

    from app.services.conflicts import find_conflicts
    from app.services.findings import save_conflicts

    db = SessionLocal()

    try:
        document_ids = state.get(
            "document_ids",
            [],
        )

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


def _normalize(text: str) -> str:
    return " ".join(
        re.sub(
            r"[^a-z0-9$%.]+",
            " ",
            text.lower(),
        ).split()
    )


def _extract_expected_value(rule: str) -> str | None:
    patterns = [
        r"\bmust be\s+(.+)$",
        r"\bshould be\s+(.+)$",
        r"\bhas to be\s+(.+)$",
        r"\bneeds to be\s+(.+)$",
        r"\brequired to be\s+(.+)$",
        r"\bshall be\s+(.+)$",
    ]

    normalized = rule.strip()

    for pattern in patterns:
        match = re.search(
            pattern,
            normalized,
            flags=re.IGNORECASE,
        )

        if match:
            return match.group(1).strip(
                " .,:;"
            )

    return None


def _find_matching_facts(
    rule: str,
    facts,
):
    rule_normalized = _normalize(rule)

    matches = []

    for fact in facts:
        fact_name = _normalize(fact.fact)

        if not fact_name:
            continue

        if fact_name in rule_normalized:
            matches.append(fact)

    return matches


def rule_check_node(
    state: AgentState,
) -> AgentState:
    started_at = time.perf_counter()

    from app.db.models import ExtractedFactModel, Finding

    db = SessionLocal()

    try:
        rules = [
            rule.strip()
            for rule in state.get("rules", [])
            if rule and rule.strip()
        ]

        document_ids = state.get(
            "document_ids",
            [],
        )

        rule_finding_ids = []

        if not rules:
            return save_stage_checkpoint(
                "rule_check",
                {
                    **state,
                    "rule_finding_ids": [],
                },
                started_at,
            )

        facts = (
            db.query(ExtractedFactModel)
            .filter(
                ExtractedFactModel.document_id.in_(
                    document_ids
                )
            )
            .order_by(
                ExtractedFactModel.id
            )
            .all()
        )

        for document_id in document_ids:
            document_facts = [
                fact
                for fact in facts
                if fact.document_id == document_id
            ]

            for rule in rules:
                matches = _find_matching_facts(
                    rule,
                    document_facts,
                )

                if not matches:
                    finding = Finding(
                        document_id=document_id,
                        finding_type="rule",
                        description=(
                            "Rule could not be verified "
                            f"from extracted facts: {rule}"
                        ),
                        fact_ids=json_ids([]),
                        status="pending",
                    )

                    db.add(finding)
                    db.flush()

                    rule_finding_ids.append(
                        finding.id
                    )

                    continue

                expected = _extract_expected_value(
                    rule
                )

                if expected is None:
                    continue

                expected_normalized = _normalize(
                    expected
                )

                for fact in matches:
                    actual_normalized = _normalize(
                        fact.value
                    )

                    if (
                        expected_normalized
                        != actual_normalized
                    ):
                        finding = Finding(
                            document_id=document_id,
                            finding_type="rule",
                            description=(
                                f"Rule violation: {rule}. "
                                f"Extracted value for "
                                f"'{fact.fact}' is "
                                f"'{fact.value}'."
                            ),
                            fact_ids=json_ids(
                                [fact.id]
                            ),
                            status="pending",
                        )

                        db.add(finding)
                        db.flush()

                        rule_finding_ids.append(
                            finding.id
                        )

        db.commit()

        elapsed = round(
            time.perf_counter() - started_at,
            4,
        )

        updated = {
            **state,
            "current_stage": "rule_check",
            "status": "completed",
            "rule_finding_ids": rule_finding_ids,
            "finding_ids": [
                *state.get(
                    "finding_ids",
                    [],
                ),
                *rule_finding_ids,
            ],
            "stage_timings": {
                **state.get("stage_timings", {}),
                "rule_check": elapsed,
            },
        }

        save_checkpoint(
            db,
            state["run_id"],
            updated,
            stage="rule_check",
            status="completed",
        )

        return updated

    finally:
        db.close()


def json_ids(ids: list[int]) -> str:
    import json

    return json.dumps(ids)


def route_after_conflict_check(
    state: AgentState,
):
    rules = [
        rule.strip()
        for rule in state.get("rules", [])
        if rule and rule.strip()
    ]

    if rules:
        return "rule_check"

    return "draft"


def draft_node(state: AgentState) -> AgentState:
    started_at = time.perf_counter()

    from app.services.draft import build_draft

    db = SessionLocal()

    try:
        document_ids = state.get(
            "document_ids",
            [],
        )

        drafts = []

        for document_id in document_ids:
            drafts.append(
                build_draft(
                    db,
                    document_id,
                )
            )

        draft = "\n\n".join(drafts)

        elapsed = round(
            time.perf_counter() - started_at,
            4,
        )

        updated = {
            **state,
            "current_stage": "draft",
            "status": "completed",
            "draft": draft,
            "stage_timings": {
                **state.get("stage_timings", {}),
                "draft": elapsed,
            },
        }

        save_checkpoint(
            db,
            state["run_id"],
            updated,
            stage="draft",
            status="completed",
        )

        return updated

    finally:
        db.close()


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
        if state.get("rules"):
            return "rule_check"

        return "draft"

    if stage == "rule_check":
        return "draft"

    if stage == "draft":
        return "review"

    if stage == "review":
        return "review"

    return "ingest"


def build_graph():
    graph = StateGraph(AgentState)

    graph.add_node(
        "ingest",
        ingest_node,
    )

    graph.add_node(
        "extract",
        extract_node,
    )

    graph.add_node(
        "conflict_check",
        conflict_check_node,
    )

    graph.add_node(
        "rule_check",
        rule_check_node,
    )

    graph.add_node(
        "draft",
        draft_node,
    )

    graph.add_node(
        "review",
        review_node,
    )

    graph.add_conditional_edges(
        START,
        route_start,
        {
            "ingest": "ingest",
            "extract": "extract",
            "conflict_check": "conflict_check",
            "rule_check": "rule_check",
            "draft": "draft",
            "review": "review",
        },
    )

    graph.add_edge(
        "ingest",
        "extract",
    )

    graph.add_conditional_edges(
        "extract",
        route_after_extract,
        {
            "conflict_check": "conflict_check",
            "retry_extract": "extract",
            "escalate_review": "review",
        },
    )

    graph.add_conditional_edges(
        "conflict_check",
        route_after_conflict_check,
        {
            "rule_check": "rule_check",
            "draft": "draft",
        },
    )

    graph.add_edge(
        "rule_check",
        "draft",
    )

    graph.add_edge(
        "draft",
        "review",
    )

    graph.add_edge(
        "review",
        END,
    )

    return graph.compile()