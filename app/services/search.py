from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import DocumentChunk
from app.services.embeddings import embed_text


GROUNDING_DISTANCE_THRESHOLD = 0.45


def search_chunks(
    db: Session,
    query: str,
    limit: int = 5,
) -> list[DocumentChunk]:
    query_embedding = embed_text(query)

    stmt = (
        select(DocumentChunk)
        .where(
            DocumentChunk.embedding.is_not(None)
        )
        .order_by(
            DocumentChunk.embedding.cosine_distance(
                query_embedding
            )
        )
        .limit(limit)
    )

    return list(
        db.scalars(stmt).all()
    )


def search_grounded_chunks(
    db: Session,
    query: str,
    limit: int = 5,
) -> list[tuple[DocumentChunk, float]]:
    """
    Return only chunks whose vector distance is
    strong enough to be considered supporting evidence.

    The distance is returned alongside each chunk so
    callers can make the grounding decision explicit.
    """

    query_embedding = embed_text(query)

    distance = (
        DocumentChunk.embedding.cosine_distance(
            query_embedding
        )
    )

    stmt = (
        select(
            DocumentChunk,
            distance.label("distance"),
        )
        .where(
            DocumentChunk.embedding.is_not(None)
        )
        .order_by(distance)
        .limit(limit)
    )

    results = db.execute(stmt).all()

    grounded = []

    for chunk, chunk_distance in results:
        if (
            chunk_distance
            <= GROUNDING_DISTANCE_THRESHOLD
        ):
            grounded.append(
                (
                    chunk,
                    float(chunk_distance),
                )
            )

    return grounded


def answer_grounded_claim(
    db: Session,
    query: str,
    limit: int = 5,
) -> dict:
    """
    Deterministic source-grounded claim lookup.

    If the available document chunks do not provide
    sufficiently close evidence, explicitly report that
    the claim is unsupported instead of guessing.
    """

    results = search_grounded_chunks(
        db,
        query,
        limit=limit,
    )

    if not results:
        return {
            "supported": False,
            "answer": (
                "Not supported by the provided documents."
            ),
            "sources": [],
        }

    sources = []

    for chunk, distance in results:
        sources.append(
            {
                "document_id": chunk.document_id,
                "chunk_id": chunk.id,
                "page_number": chunk.page_number,
                "section": chunk.section,
                "distance": round(
                    distance,
                    4,
                ),
                "content": chunk.content,
            }
        )

    return {
        "supported": True,
        "answer": (
            "The provided documents contain "
            "supporting evidence for this claim."
        ),
        "sources": sources,
    }