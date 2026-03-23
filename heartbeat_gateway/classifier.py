from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import litellm
import yaml
from loguru import logger

from heartbeat_gateway import HeartbeatEntry, NormalizedEvent
from heartbeat_gateway.config.schema import GatewayConfig

_PROMPT_PATH = Path(__file__).parent / "prompts" / "classify.yaml"
_VALID_VERDICTS = {"ACTIONABLE", "DELTA", "IGNORE"}


@dataclass
class ClassifierVerdict:
    verdict: Literal["ACTIONABLE", "DELTA", "IGNORE"]
    rationale: str
    entry: HeartbeatEntry | None = None  # populated only when ACTIONABLE


def _load_prompt_template() -> str:
    with open(_PROMPT_PATH) as f:
        return yaml.safe_load(f)["template"]


def _render(template: str, **kwargs: str) -> str:
    result = template
    for key, value in kwargs.items():
        result = result.replace("{{ " + key + " }}", value)
    return result


def _read_soul_excerpt(path: Path, max_chars: int = 500) -> str:
    try:
        return path.read_text(encoding="utf-8")[:max_chars]
    except OSError:
        return ""


def _read_current_tasks(heartbeat_path: Path, max_chars: int = 1200) -> str:
    try:
        content = heartbeat_path.read_text(encoding="utf-8")
    except OSError:
        return ""
    idx = content.find("## Active Tasks")
    if idx == -1:
        return ""
    lines = content[idx:].splitlines()
    return "\n".join(lines[-10:])[:max_chars]


class Classifier:
    def __init__(self, config: GatewayConfig) -> None:
        self._config = config
        self._template = _load_prompt_template()

    async def classify(self, event: NormalizedEvent) -> ClassifierVerdict:
        soul_excerpt = _read_soul_excerpt(
            self._config.soul_md_path,
            max_chars=self._config.soul_excerpt_chars,
        )
        current_tasks = _read_current_tasks(
            self._config.workspace_path / "HEARTBEAT.md",
            max_chars=self._config.active_tasks_chars,
        )

        prompt = _render(
            self._template,
            soul_excerpt=soul_excerpt,
            source=event.source,
            event_summary=event.payload_condensed,
            current_tasks=current_tasks,
        )

        api_key = self._config.llm_api_key or None
        try:
            try:
                response = await litellm.acompletion(
                    model=self._config.llm_model,
                    api_key=api_key,
                    messages=[{"role": "user", "content": prompt}],
                    response_format={"type": "json_object"},
                )
            except litellm.UnsupportedParamsError:
                # response_format not supported for this model/version — retry without it
                response = await litellm.acompletion(
                    model=self._config.llm_model,
                    api_key=api_key,
                    messages=[{"role": "user", "content": prompt}],
                )
            raw = response.choices[0].message.content or ""
            raw = raw.strip()
            if raw.startswith("```"):
                # Strip markdown code fencing the model may add despite prompt instructions
                raw = raw.split("\n", 1)[-1].rsplit("```", 1)[0].strip()
            data = json.loads(raw)
            verdict_str: str = data["classification"]
        except Exception as exc:
            logger.error("Classifier error ({}: {})", type(exc).__name__, exc)
            return ClassifierVerdict(verdict="IGNORE", rationale="classifier error")

        if verdict_str not in _VALID_VERDICTS:
            return ClassifierVerdict(verdict="IGNORE", rationale="classifier error")

        rationale: str = data.get("rationale", "")

        if verdict_str == "ACTIONABLE":
            url = event.metadata.get("issue_url") or event.metadata.get("pr_url")
            priority: Literal["high", "normal"] = (
                "high" if "failure" in event.event_type or "blocked" in event.event_type else "normal"
            )
            entry = HeartbeatEntry(
                source=event.source,
                event_type=event.event_type,
                title=rationale[:120],
                timestamp=event.timestamp,
                payload_condensed=event.payload_condensed,
                url=url,
                priority=priority,
            )
            return ClassifierVerdict(verdict="ACTIONABLE", rationale=rationale, entry=entry)

        if verdict_str == "DELTA":
            return ClassifierVerdict(verdict="DELTA", rationale=rationale, entry=None)

        return ClassifierVerdict(verdict="IGNORE", rationale=rationale, entry=None)
