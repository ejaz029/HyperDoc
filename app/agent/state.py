from typing import TypedDict


class AgentState(TypedDict, total=False):
    run_id: int
    document_ids: list[int]

    # User-provided rules/checklist items.
    rules: list[str]

    current_stage: str
    status: str

    extracted_fact_ids: list[int]
    extraction_attempts: int
    finding_ids: list[int]

    # Findings generated specifically from rule/checklist examination.
    rule_finding_ids: list[int]

    draft: str

    stage_timings: dict[str, float]
    total_duration_seconds: float
    llm_usage: dict[str, int]

    error: str | None