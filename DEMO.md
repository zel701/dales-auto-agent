# Negotiation demo

The `/demo` page opens without an invitation code or login. Select **Try demo**, **Approve & send**, then **Retry send**. The first send is rejected once, and the draft stays pending. After retrying, select **Simulate dealer reply** to continue through availability, itemized pricing, discount, scheduling, and appointment confirmation.

The demo uses the same negotiation graph, interrupt handling, and send-success check as the application. It uses a sample Toyota Camry order and canned drafts and dealer replies. The demo API does not expose the regular review console, dealership webhook, or customer routes. It uses no API keys or application database.

## Run locally

From the repository root, start the Python demo API:

```sh
cd agent
uv run uvicorn car_agent.api.demo:app --host 127.0.0.1 --port 8022
```

In a second terminal, start Next.js from the repository root:

```sh
cd website
npm ci
DEMO_API_URL=http://127.0.0.1:8022 npm run dev -- --port 3022
```

Open [http://localhost:3022/demo](http://localhost:3022/demo). `DEMO_API_URL` is server-side and enables the demo page and its API. Each browser gets an HTTP-only session cookie. Refreshing restores the current step, and **Start over** resets the scenario.

## Host a portfolio instance

Deploy `agent/` as a private Python service. Install with `pip install .` and start with `uvicorn car_agent.api.demo:app --host 0.0.0.0 --port "$PORT"`. Use the demo API's `/health` endpoint for readiness checks.

Deploy `website/` as a public Next.js service. Build with `npm ci && npm run build` and start with `npm run start -- --port "$PORT"`. Set `DEMO_API_URL` to the private Python service's URL, including its listening port. Link visitors directly to the public `/demo` page over HTTPS.

Run one Python worker and one replica. Demo sessions live in memory, expire after 30 minutes, and are reset on service restart. The API caps the number of active sessions at 256. Keep the regular API entry point and its credentials in the application environment.
