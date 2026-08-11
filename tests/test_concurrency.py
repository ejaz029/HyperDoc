from concurrent.futures import ThreadPoolExecutor

from app.agent.runner import run_agent


def test_concurrent_agent_runs_are_isolated():
    document_ids = [1, 18]

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(run_agent, [document_id])
            for document_id in document_ids
        ]

        results = [future.result() for future in futures]

    assert len(results) == 2

    run_document_ids = {
        tuple(result["document_ids"])
        for result in results
    }

    assert run_document_ids == {(1,), (18,)}

    for result in results:
        assert result["current_stage"] == "review"
        assert result["status"] == "waiting_for_review"