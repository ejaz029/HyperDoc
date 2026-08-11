from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DocumentChunk
from app.services.embeddings import embed_text


def search_chunks(
    db: Session,
    query: str,
    limit: int = 5,
) -> list[DocumentChunk]:
    query_embedding = embed_text(query)

    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.embedding.is_not(None))
        .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
        .limit(limit)
    )

    return list(db.scalars(stmt).all())