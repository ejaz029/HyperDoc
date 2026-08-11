from app.agent.graph import build_graph


def test_agent_graph():
    graph = build_graph()

    result = graph.invoke(
        {
            "run_id": 1,
            "document_ids": [1],
            "status": "pending",
        }
    )

    assert result["current_stage"] == "review"
    assert result["status"] == "waiting_for_review"