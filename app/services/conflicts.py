from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ExtractedFactModel


@dataclass
class ConflictFinding:
    fact: str
    values: list[str]
    fact_ids: list[int]


def _normalize_fact_name(value: str) -> str:
    return " ".join(
        value.strip().lower().split()
    )


def _unique_values(
    facts: list[ExtractedFactModel],
) -> list[str]:
    values = []

    for fact in facts:
        value = fact.value.strip()

        if value not in values:
            values.append(value)

    return values


def find_conflicts(
    db: Session,
    document_id: int,
) -> list[ConflictFinding]:
    """
    Detect conflicts inside a single document.

    Existing behavior is preserved:
    facts are grouped by normalized fact name and a
    conflict is produced when the same fact has multiple
    distinct values.
    """

    facts = list(
        db.scalars(
            select(ExtractedFactModel)
            .where(
                ExtractedFactModel.document_id
                == document_id
            )
        )
    )

    grouped: dict[
        str,
        list[ExtractedFactModel],
    ] = {}

    for fact in facts:
        key = _normalize_fact_name(
            fact.fact
        )

        grouped.setdefault(
            key,
            [],
        ).append(fact)

    conflicts = []

    for fact_name, items in grouped.items():
        values = _unique_values(items)

        if len(values) > 1:
            conflicts.append(
                ConflictFinding(
                    fact=fact_name,
                    values=values,
                    fact_ids=[
                        item.id
                        for item in items
                    ],
                )
            )

    return conflicts


def find_incremental_conflicts(
    db: Session,
    document_id: int,
) -> list[ConflictFinding]:
    """
    Detect conflicts introduced by a newly ingested
    document when compared with facts from earlier
    documents.

    The new document is compared against all facts
    belonging to other documents.

    The existing document-local conflict behavior
    remains handled by find_conflicts().
    """

    new_facts = list(
        db.scalars(
            select(ExtractedFactModel)
            .where(
                ExtractedFactModel.document_id
                == document_id
            )
        )
    )

    if not new_facts:
        return []

    previous_facts = list(
        db.scalars(
            select(ExtractedFactModel)
            .where(
                ExtractedFactModel.document_id
                != document_id
            )
        )
    )

    if not previous_facts:
        return []

    previous_by_name: dict[
        str,
        list[ExtractedFactModel],
    ] = {}

    for fact in previous_facts:
        key = _normalize_fact_name(
            fact.fact
        )

        previous_by_name.setdefault(
            key,
            [],
        ).append(fact)

    new_by_name: dict[
        str,
        list[ExtractedFactModel],
    ] = {}

    for fact in new_facts:
        key = _normalize_fact_name(
            fact.fact
        )

        new_by_name.setdefault(
            key,
            [],
        ).append(fact)

    conflicts = []

    for fact_name, current_items in new_by_name.items():
        previous_items = previous_by_name.get(
            fact_name,
            [],
        )

        if not previous_items:
            continue

        current_values = _unique_values(
            current_items
        )

        previous_values = _unique_values(
            previous_items
        )

        all_values = []

        for value in (
            previous_values
            + current_values
        ):
            if value not in all_values:
                all_values.append(value)

        if len(all_values) <= 1:
            continue

        conflicts.append(
            ConflictFinding(
                fact=fact_name,
                values=all_values,
                fact_ids=[
                    item.id
                    for item in previous_items
                    + current_items
                ],
            )
        )

    return conflicts