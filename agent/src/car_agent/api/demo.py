"""Standalone FastAPI entry point that exposes only the demo endpoints."""

from time import monotonic
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel, Field

from car_agent.services.demo_negotiation import DemoAction, DemoSession, DemoState

MAX_SESSIONS = 256


class SessionState(BaseModel):
    session_id: UUID
    state: DemoState


class ActionRequest(BaseModel):
    action: DemoAction
    revision: int = Field(ge=0)


def create_demo_app() -> FastAPI:
    app = FastAPI(title="Dales Auto Agent Demo", docs_url=None, redoc_url=None, openapi_url=None)
    sessions: dict[UUID, DemoSession] = {}

    def get_session(session_id: UUID) -> DemoSession:
        session = sessions.get(session_id)
        if session is None or session.expires_at <= monotonic():
            raise HTTPException(status_code=404, detail="Demo session expired.")
        return session

    @app.get("/health")
    async def health():
        return {"status": "ok"}

    @app.post("/sessions", status_code=201)
    async def start() -> SessionState:
        now = monotonic()
        for key in [key for key, session in sessions.items() if session.expires_at <= now]:
            del sessions[key]
        if len(sessions) >= MAX_SESSIONS:
            raise HTTPException(status_code=429, detail="The demo is busy. Please try again later.")
        session_id = uuid4()
        session = sessions[session_id] = DemoSession()
        async with session.lock:
            try:
                state = await session.start()
            except BaseException:
                sessions.pop(session_id, None)
                raise
        return SessionState(session_id=session_id, state=state)

    @app.get("/sessions/{session_id}")
    async def state(session_id: UUID) -> DemoState:
        session = get_session(session_id)
        async with session.lock:
            return await session.state()

    @app.post("/sessions/{session_id}")
    async def act(session_id: UUID, body: ActionRequest, response: Response) -> DemoState:
        session = get_session(session_id)
        async with session.lock:
            state, response.status_code = await session.act(body.action, body.revision)
        return state

    return app


app = create_demo_app()
