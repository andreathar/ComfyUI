from unittest.mock import MagicMock, patch

import pytest
from aiohttp.test_utils import TestClient, TestServer

import server


async def _client():
    prompt_server = server.PromptServer(None, MagicMock(enabled=False))
    prompt_server.app.add_routes(prompt_server.routes)
    return TestClient(TestServer(prompt_server.app)), prompt_server


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("query", "error"),
    [
        ("max_items=invalid", "max_items must be an integer"),
        ("offset=invalid", "offset must be an integer"),
    ],
)
async def test_history_rejects_non_integer_pagination(query, error):
    client, _ = await _client()
    async with client:
        response = await client.get(f"/history?{query}")
        assert response.status == 400
        assert await response.json() == {"error": error}


@pytest.mark.asyncio
async def test_targeted_interrupt_uses_atomic_queue_check():
    client, prompt_server = await _client()
    with (
        patch.object(prompt_server.prompt_queue, "interrupt_if_running", return_value=False) as interrupt,
        patch("nodes.interrupt_processing") as global_interrupt,
    ):
        async with client:
            response = await client.post("/interrupt", json={"prompt_id": "job-id"})

    assert response.status == 200
    interrupt.assert_called_once_with("job-id")
    global_interrupt.assert_not_called()


@pytest.mark.asyncio
async def test_targeted_interrupt_dispatches_for_the_matching_running_job():
    client, prompt_server = await _client()
    prompt_server.prompt_queue.currently_running[0] = (0, "job-id", {}, {}, [])

    with patch("nodes.interrupt_processing") as global_interrupt:
        async with client:
            response = await client.post("/interrupt", json={"prompt_id": "job-id"})

    assert response.status == 200
    global_interrupt.assert_called_once_with()
