from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ExtractedFactModel


def build_draft(
    db: Session,
    document_id: int,
) -> str:
    facts = list(
        db.scalars(
            select(ExtractedFactModel)
            .where(
                ExtractedFactModel.document_id == document_id
            )
            .order_by(ExtractedFactModel.id)
        )
    )

    if not facts:
        return "No extracted facts available."

    lines = [
        "# Vendor Contract Brief",
        "",
        "## Extracted Facts",
        "",
    ]

    for fact in facts:
        source = f"Document {fact.document_id}"

        if fact.page_number is not None:
            source += f", Page {fact.page_number}"

        if fact.section:
            source += f", Section: {fact.section}"

        lines.append(
            f"- **{fact.fact}:** {fact.value} "
            f"— *Source: {source}, Chunk {fact.chunk_id}*"
        )

    return "\n".join(lines)