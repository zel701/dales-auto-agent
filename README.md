# Dales Auto Agent

**[Try the live demo](https://dales-auto-demo.up.railway.app/demo)** · [Run the demo locally](DEMO.md)

Dales Auto Agent is a collaborative car-buying assistant. It searches Toyota inventory, accepts negotiation requests, and assists buyers through dealer conversations. An operator reviews each draft before the agent sends it.

The public demo starts with a sample Toyota Camry order. Choose **Try demo**, **Approve & send**, and **Retry send** to see how a failed send leaves the review pending. You can then simulate dealer replies through availability, itemized pricing, discount, scheduling, and appointment confirmation. The demo uses the same LangGraph workflow with simulated inventory, messages, and dealer replies.

## Source code

| Area | Implementation |
| --- | --- |
| Web app | [Next.js, React, and TypeScript](website/src) for inventory results, buyer intake, and the review console |
| Application API | [Python and FastAPI](agent/src/car_agent/api/app.py) with [MarketCheck inventory search](agent/src/car_agent/clients/marketcheck.py) and [Resend email](agent/src/car_agent/clients/email.py) |
| Negotiation | [LangGraph workflow](agent/src/car_agent/graph.py) with [approval and dealer reply interrupts](agent/src/car_agent/nodes/negotiation_v2.py) |
| Demo | [Web interface](website/src/app/demo) and [isolated FastAPI service](agent/src/car_agent/api/demo.py) reuse the negotiation graph with sample data |

## Contributors

This is a team project by [Joseph Zhao](https://github.com/josephzha) and [Erlin Zhao](https://github.com/zel701). Erlin's contributions include a [fix to keep failed email sends retryable](https://github.com/zel701/dales-auto-agent/commit/efdab2b5aa91800163c54a4997ff5c9e6ddb40d7), [regression tests for the approval endpoint](agent/tests/test_review_approval.py), and the [public demo flow and its integration test](agent/tests/test_demo_api.py).

## Local development

Start with [Demo mode](DEMO.md) to run both services with sample data and no vendor credentials. The full application's backend entry point is `car_agent.api.app:app` and its environment template is [agent/.env.example](agent/.env.example). `LANGGRAPH_API_URL` connects the Next.js server to the full API. `DEMO_API_URL` connects it to the demo API.

Run the backend tests with Python 3.11+ and `uv`:

```sh
cd agent
uv run --extra dev pytest
```

Run the frontend tests and production build with Node.js 22:

```sh
cd website
npm ci
npm test
npm run build
```
