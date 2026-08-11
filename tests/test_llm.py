from app.services.llm import llm


def test_groq_connection():
    response = llm.invoke("Reply with exactly: OK")

    assert response.content.strip() == "OK"