from __future__ import annotations

import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from loguru import logger

from heartbeat_gateway.adapters.github import GitHubAdapter
from heartbeat_gateway.adapters.linear import LinearAdapter
from heartbeat_gateway.adapters.posthog import PostHogAdapter
from heartbeat_gateway.classifier import Classifier
from heartbeat_gateway.config.schema import GatewayConfig
from heartbeat_gateway.pre_filter import PreFilter
from heartbeat_gateway.writer import HeartbeatWriter

VERSION = "0.1.0"


async def _process_webhook(request: Request, source: str):
    body = await request.body()
    headers = dict(request.headers)
    state = request.app.state
    adapter = getattr(state, f"{source}_adapter")

    try:
        if not adapter.verify_signature(body, headers):
            return JSONResponse({"status": "unauthorized"}, status_code=401)

        payload = json.loads(body)
        event = adapter.normalize(payload, headers)

        if event is None:
            return {"status": "ignored"}

        should_drop, _ = state.pre_filter.should_drop(event, state.config)
        if should_drop:
            return {"status": "ignored"}

        verdict = await state.classifier.classify(event)

        if verdict.verdict == "ACTIONABLE":
            state.writer.write_actionable(verdict.entry)
            return {"status": "actionable"}
        if verdict.verdict == "DELTA":
            state.writer.write_delta(event)
            return {"status": "delta"}
        return {"status": "ignored"}

    except Exception as exc:
        logger.error("Unhandled exception in {} webhook: {}", source, exc)
        return JSONResponse({"status": "error"}, status_code=500)


def create_app(config: GatewayConfig | None = None) -> FastAPI:
    if config is None:
        config = GatewayConfig()

    app = FastAPI()
    app.state.config = config
    app.state.pre_filter = PreFilter()
    app.state.classifier = Classifier(config)
    app.state.writer = HeartbeatWriter(config)
    app.state.linear_adapter = LinearAdapter(config)
    app.state.github_adapter = GitHubAdapter(config)
    app.state.posthog_adapter = PostHogAdapter(config)

    @app.post("/webhooks/linear")
    async def linear_webhook(request: Request):
        return await _process_webhook(request, "linear")

    @app.post("/webhooks/github")
    async def github_webhook(request: Request):
        return await _process_webhook(request, "github")

    @app.post("/webhooks/posthog")
    async def posthog_webhook(request: Request):
        return await _process_webhook(request, "posthog")

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": VERSION}

    return app
