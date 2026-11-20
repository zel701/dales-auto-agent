"""FastAPI application factory with lifespan management."""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from car_agent.api.routes import (
    analyze,
    auth,
    invites,
    negotiate,
    results,
    reviews,
    webhooks,
)
from car_agent.checkpointer import make_checkpointer
from car_agent.db.database import init_db
from car_agent.graph import builder
from car_agent.logging_config import configure_logging

logger = logging.getLogger(__name__)

graph = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global graph
    configure_logging()
    await init_db()
    async with make_checkpointer() as checkpointer:
        graph = builder.compile(checkpointer=checkpointer)
        logger.info("Database initialized, graph compiled")
        yield


app = FastAPI(title="Car Agent API", lifespan=lifespan)

_origins = [
    o.strip()
    for o in os.environ.get("WEBSITE_URL", "http://localhost:3000").split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(auth.router)
app.include_router(invites.router)
app.include_router(results.router)
app.include_router(negotiate.router)
app.include_router(reviews.router)
app.include_router(webhooks.router)


@app.get("/health")
async def health():
    return {"status": "ok"}
