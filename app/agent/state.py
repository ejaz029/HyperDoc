from typing import TypedDict


class AgentState(TypedDict, total=False):
    run_id: int
    document_ids: list[int]

    current_stage: str
    status: str

    extracted_fact_ids: list[int]
    finding_ids: list[int]

    draft: str

    error: str | None