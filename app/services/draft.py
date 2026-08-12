from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import ExtractedFactModel


def _source_text(fact: ExtractedFactModel) -> str:
    source = f"Document {fact.document_id}"

    if fact.page_number is not None:
        source += f", Page {fact.page_number}"

    if fact.section:
        source += f", Section: {fact.section}"

    return (
        f"{source}, Chunk {fact.chunk_id}"
    )


def build_draft(
    db: Session,
    document_id: int,
) -> str:
    facts = list(
        db.scalars(
            select(ExtractedFactModel)
            .where(
                ExtractedFactModel.document_id
                == document_id
            )
            .order_by(
                ExtractedFactModel.id
            )
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
        source = _source_text(fact)

        lines.append(
            f"- **{fact.fact}:** {fact.value} "
            f"— *Source: {source}*"
        )

    return "\n".join(lines)


def build_incremental_update(
    db: Session,
    new_document_id: int,
) -> str:
    """
    Build a focused update containing only facts
    introduced by the newly ingested document.

    Existing document facts are deliberately not
    regenerated here.
    """

    facts = list(
        db.scalars(
            select(ExtractedFactModel)
            .where(
                ExtractedFactModel.document_id
                == new_document_id
            )
            .order_by(
                ExtractedFactModel.id
            )
        )
    )

    if not facts:
        return (
            "# Incremental Document Update\n\n"
            "No new extracted facts available."
        )

    lines = [
        "# Incremental Document Update",
        "",
        f"New Document: {new_document_id}",
        "",
        "## New Facts",
        "",
    ]

    for fact in facts:
        source = _source_text(fact)

        lines.append(
            f"- **{fact.fact}:** {fact.value} "
            f"— *Source: {source}*"
        )

    return "\n".join(lines)