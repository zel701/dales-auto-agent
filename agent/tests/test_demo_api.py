import asyncio

from httpx import ASGITransport, AsyncClient

from car_agent.api.demo import create_demo_app


async def test_demo_retries_keeps_sessions_separate_and_finishes_all_stages():
    async with AsyncClient(transport=ASGITransport(app=create_demo_app()), base_url="http://test") as client:
        async def start():
            response = await client.post("/sessions")
            assert response.status_code == 201
            data = response.json()
            return f"/sessions/{data['session_id']}", data["state"]

        async def act(url, action, state):
            return await client.post(url, json={"action": action, "revision": state["revision"]})

        path, initial = await start()
        other_path, other_initial = await start()
        assert path != other_path and initial["status"] == "approval"

        # Two copies of one click must not consume the retry as well as the failure.
        clicks = await asyncio.gather(act(path, "send", initial), act(path, "send", initial))
        by_status = {response.status_code: response.json() for response in clicks}
        assert set(by_status) == {409, 502}
        failed = by_status[502]
        assert failed["status"] == "approval" and failed["stage"] == 1
        assert failed["error"] and failed["draft"] == initial["draft"]
        assert (await client.get(other_path)).json() == other_initial
        assert (await act(other_path, "send", other_initial)).status_code == 502

        state = failed
        for stage in range(1, 6):
            assert state["stage"] == stage and state["status"] == "approval"
            sent = (await act(path, "send", state)).raise_for_status().json()
            assert sent["status"] == "dealer_reply" and sent["error"] is None
            state = (await act(path, "reply", sent)).raise_for_status().json()

        assert state["status"] == "appointment_set" and state["appointment"]
        assert state["latest_reply"] == f"Confirmed for {state['appointment']} at Demo Toyota."
        restarted = (await act(path, "restart", state)).raise_for_status().json()
        assert restarted["stage"] == 1 and restarted["appointment"] is None
        assert (await act(path, "send", restarted)).status_code == 502

        assert (await client.get("/api/reviews")).status_code == 404
        assert (await client.post("/resend/inbound")).status_code == 404
