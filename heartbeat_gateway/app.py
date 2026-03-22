from __future__ import annotations

import json

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, RedirectResponse
from loguru import logger

from heartbeat_gateway.adapters.github import GitHubAdapter
from heartbeat_gateway.adapters.linear import LinearAdapter
from heartbeat_gateway.adapters.posthog import PostHogAdapter
from heartbeat_gateway.classifier import Classifier
from heartbeat_gateway.config.schema import GatewayConfig
from heartbeat_gateway.pre_filter import PreFilter
from heartbeat_gateway.writer import HeartbeatWriter

VERSION = "0.1.1"


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
            return {"status": "ignored", "reason": "unrecognized_event_type"}

        should_drop, reason = state.pre_filter.should_drop(event, state.config)
        if should_drop:
            return {"status": "ignored", "reason": reason}

        verdict = await state.classifier.classify(event)

        if verdict.verdict == "ACTIONABLE":
            state.writer.write_actionable(verdict.entry)
            state.writer.write_audit(event, "ACTIONABLE", verdict.rationale)
            return {"status": "actionable"}
        if verdict.verdict == "DELTA":
            state.writer.write_delta(event)
            state.writer.write_audit(event, "DELTA", verdict.rationale)
            return {"status": "delta"}
        state.writer.write_audit(event, "IGNORE", verdict.rationale)
        return {"status": "ignored", "reason": verdict.rationale}

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

    # Redirect singular /webhook/{source} → /webhooks/{source} (308 preserves POST method)
    @app.post("/webhook/linear", include_in_schema=False)
    async def redirect_linear():
        return RedirectResponse(url="/webhooks/linear", status_code=308)

    @app.post("/webhook/github", include_in_schema=False)
    async def redirect_github():
        return RedirectResponse(url="/webhooks/github", status_code=308)

    @app.post("/webhook/posthog", include_in_schema=False)
    async def redirect_posthog():
        return RedirectResponse(url="/webhooks/posthog", status_code=308)

    @app.get("/health")
    async def health():
        return {"status": "ok", "version": VERSION}

    return app


def main() -> None:
    import uvicorn

    uvicorn.run("heartbeat_gateway.app:create_app", factory=True, host="0.0.0.0", port=8080)
