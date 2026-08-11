from app.services.embeddings import embed_text


def test_embedding_dimension():
    embedding = embed_text("Vendor contract payment terms")

    assert len(embedding) == 384