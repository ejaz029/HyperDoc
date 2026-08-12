import os

import pytest


@pytest.mark.skipif(
    os.getenv("RUN_LIVE_LLM_TESTS") != "1",
    reason="Live LLM test disabled; set RUN_LIVE_LLM_TESTS=1 to enable.",
)
def test_groq_connection():
    from app.services.llm import llm

    response = llm.invoke(
        "Reply with exactly: OK"
    )

    assert response.content.strip() == "OK"