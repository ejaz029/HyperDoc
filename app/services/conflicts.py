from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ExtractedFactModel


@dataclass
class ConflictFinding:
    fact: str
    values: list[str]
    fact_ids: list[int]


def find_conflicts(
    db: Session,
    document_id: int,
) -> list[ConflictFinding]:
    facts = list(
        db.scalars(
            select(ExtractedFactModel)
            .where(
                ExtractedFactModel.document_id == document_id
            )
        )
    )

    grouped: dict[str, list[ExtractedFactModel]] = {}

    for fact in facts:
        key = fact.fact.strip().lower()
        grouped.setdefault(key, []).append(fact)

    conflicts = []

    for fact_name, items in grouped.items():
        values = list(dict.fromkeys(item.value for item in items))

        if len(values) > 1:
            conflicts.append(
                ConflictFinding(
                    fact=fact_name,
                    values=values,
                    fact_ids=[item.id for item in items],
                )
            )

    return conflicts