"""gateway doctor — pre-flight config validator.

CONSTRAINT: Do NOT import from heartbeat_gateway.app. Import only from
heartbeat_gateway.config.schema and heartbeat_gateway.config.loader.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field  # noqa: F401
from enum import Enum

import click
from rich import box
from rich.console import Console
from rich.table import Table

from heartbeat_gateway.config.schema import GatewayConfig

# Replicated from app.py — do NOT import from app.py (pulls in FastAPI + all adapters)
EXPECTED_MIN_BODY_BYTES = 512 * 1024  # 512 KB

UUID_V4_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
UUID_ANYWHERE_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}"
)
SOUL_SCOPING_PREFIXES = re.compile(r"^\s*(repo:|branch:|project_id:)", re.MULTILINE)

_console = Console()


class CheckStatus(str, Enum):
    PASS = "PASS"
    WARN = "WARN"
    FAIL = "FAIL"


@dataclass
class CheckResult:
    name: str
    status: CheckStatus
    message: str
    fix_hint: str = ""  # MUST be non-empty when status == FAIL


class DoctorRunner:
    """Runs all gateway doctor checks and formats results."""

    def __init__(self, verbose: bool = False) -> None:
        self.verbose = verbose

    def run(self) -> list[CheckResult]:
        """Run all checks in order. Config loaded once; passed to each check."""
        results: list[CheckResult] = []

        # Check 1: Config loads (DOC-04) — must run first; others depend on config
        config_result, config = self._check_config_loads()
        results.append(config_result)

        if config is None:
            # Can't run remaining checks without a valid config
            results.append(
                CheckResult(
                    name="Remaining checks",
                    status=CheckStatus.FAIL,
                    message="Skipped — fix config errors above first",
                    fix_hint="Re-run `gateway doctor` after fixing the config error shown above.",
                )
            )
            return results

        results.append(self._check_api_key(config))  # DOC-06
        results.append(self._check_soul_md_exists(config))  # DOC-05
        results.append(self._check_workspace_writable(config))  # workspace check
        results.extend(self._check_linear_project_ids(config))  # DOC-08
        results.extend(self._check_hmac_secrets(config))  # DOC-07
        results.append(self._check_body_size_limit())  # DOC-09

        # SOUL.md linter (DOC-10) — only if SOUL.md exists and readable
        if config.soul_md_path.exists() and os.access(config.soul_md_path, os.R_OK):
            results.extend(self._check_soul_md_content(config))

        results.extend(self._check_require_signatures_advisory(config))  # advisory

        return results

    def _check_config_loads(self) -> tuple[CheckResult, GatewayConfig | None]:
        from pydantic import ValidationError

        try:
            config = GatewayConfig()
            return (
                CheckResult(
                    name="Config loads",
                    status=CheckStatus.PASS,
                    message="GatewayConfig loaded successfully",
                ),
                config,
            )
        except ValidationError as e:
            first = e.errors()[0]
            return (
                CheckResult(
                    name="Config loads",
                    status=CheckStatus.FAIL,
                    message=f"Config validation failed: {e.error_count()} error(s)",
                    fix_hint=f"Check env vars. First error: {list(first['loc'])} — {first['msg']}",
                ),
                None,
            )

    def _check_api_key(self, config: GatewayConfig) -> CheckResult:
        if not config.llm_api_key or not config.llm_api_key.startswith("sk-ant-"):
            return CheckResult(
                name="API key format",
                status=CheckStatus.FAIL,
                message="ANTHROPIC_API_KEY missing or does not start with 'sk-ant-'",
                fix_hint=(
                    "Set ANTHROPIC_API_KEY=sk-ant-... in your .env file. "
                    "Find your key at console.anthropic.com."
                ),
            )
        return CheckResult(
            name="API key format",
            status=CheckStatus.PASS,
            message="ANTHROPIC_API_KEY present and matches sk-ant- prefix",
        )

    def _check_soul_md_exists(self, config: GatewayConfig) -> CheckResult:
        path = config.soul_md_path
        if not path.exists() or not os.access(path, os.R_OK):
            return CheckResult(
                name="SOUL.md exists",
                status=CheckStatus.FAIL,
                message=f"SOUL.md not found or not readable at {path}",
                fix_hint=f"Create SOUL.md at {path} or set GATEWAY_SOUL_MD_PATH to its actual location.",
            )
        return CheckResult(
            name="SOUL.md exists",
            status=CheckStatus.PASS,
            message=f"SOUL.md readable at {path}",
        )

    def _check_workspace_writable(self, config: GatewayConfig) -> CheckResult:
        path = config.workspace_path
        if not path.is_dir() or not os.access(path, os.W_OK):
            return CheckResult(
                name="Workspace writable",
                status=CheckStatus.FAIL,
                message=f"Workspace directory not writable: {path}",
                fix_hint=f"Create the directory or fix permissions: mkdir -p {path} && chmod 755 {path}",
            )
        return CheckResult(
            name="Workspace writable",
            status=CheckStatus.PASS,
            message=f"Workspace directory is writable: {path}",
        )

    def _check_linear_project_ids(self, config: GatewayConfig) -> list[CheckResult]:
        ids = config.watch.linear.project_ids
        if not ids:
            return [
                CheckResult(
                    name="Linear project IDs",
                    status=CheckStatus.PASS,
                    message="No Linear project IDs configured (adapter not in use)",
                )
            ]
        bad = [pid for pid in ids if not UUID_V4_PATTERN.match(pid)]
        if bad:
            return [
                CheckResult(
                    name="Linear project IDs",
                    status=CheckStatus.FAIL,
                    message=f"{len(bad)} of {len(ids)} project ID(s) are not valid UUID v4 format: {bad}",
                    fix_hint=(
                        "UUID format: xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx. "
                        "Find your project UUID in Linear via Cmd+K > 'Copy model UUID'."
                    ),
                )
            ]
        return [
            CheckResult(
                name="Linear project IDs",
                status=CheckStatus.PASS,
                message=f"All {len(ids)} Linear project ID(s) are valid UUID v4",
            )
        ]

    def _check_hmac_secrets(self, config: GatewayConfig) -> list[CheckResult]:
        results = []
        level = CheckStatus.FAIL if config.require_signatures else CheckStatus.WARN
        if not config.watch.linear.secret:
            results.append(
                CheckResult(
                    name="Linear HMAC secret",
                    status=level,
                    message="GATEWAY_WATCH__LINEAR__SECRET is not set",
                    fix_hint=(
                        "Set GATEWAY_WATCH__LINEAR__SECRET in .env. "
                        "Generate in Linear Settings > API > Webhooks."
                    ),
                )
            )
        else:
            results.append(
                CheckResult(
                    name="Linear HMAC secret",
                    status=CheckStatus.PASS,
                    message="GATEWAY_WATCH__LINEAR__SECRET is set",
                )
            )
        if not config.watch.github.secret:
            results.append(
                CheckResult(
                    name="GitHub HMAC secret",
                    status=level,
                    message="GATEWAY_WATCH__GITHUB__SECRET is not set",
                    fix_hint=(
                        "Set GATEWAY_WATCH__GITHUB__SECRET in .env. "
                        "Find in GitHub repository Settings > Webhooks."
                    ),
                )
            )
        else:
            results.append(
                CheckResult(
                    name="GitHub HMAC secret",
                    status=CheckStatus.PASS,
                    message="GATEWAY_WATCH__GITHUB__SECRET is set",
                )
            )
        return results

    def _check_body_size_limit(self) -> CheckResult:
        # EXPECTED_MIN_BODY_BYTES is replicated from app.py (do NOT import app.py).
        # This check guards against a future regression where the constant is reduced below 512KB.
        if EXPECTED_MIN_BODY_BYTES < 512 * 1024:
            return CheckResult(
                name="Body size limit",
                status=CheckStatus.FAIL,
                message=f"Body size limit ({EXPECTED_MIN_BODY_BYTES} bytes) is below 512 KB minimum",
                fix_hint=(
                    "MAX_BODY_BYTES in app.py has been reduced below 512 KB. "
                    "Restore to at least 512 * 1024 to prevent payload truncation."
                ),
            )
        return CheckResult(
            name="Body size limit",
            status=CheckStatus.PASS,
            message=f"Body size limit is {EXPECTED_MIN_BODY_BYTES // 1024} KB (>= 512 KB minimum)",
        )

    def _check_soul_md_content(self, config: GatewayConfig) -> list[CheckResult]:
        results = []
        content = config.soul_md_path.read_text(encoding="utf-8")
        uuid_matches = UUID_ANYWHERE_PATTERN.findall(content)
        if uuid_matches:
            results.append(
                CheckResult(
                    name="SOUL.md content linter (UUIDs)",
                    status=CheckStatus.WARN,
                    message=(
                        f"SOUL.md contains {len(uuid_matches)} UUID-like string(s) — "
                        f"scoping rules belong in pre_filter.py, not SOUL.md"
                    ),
                    fix_hint=(
                        "Move UUID-based project/repo scoping to GATEWAY_WATCH__LINEAR__PROJECT_IDS "
                        "or pre_filter.py. SOUL.md should contain priority and action rules only."
                    ),
                )
            )
        else:
            results.append(
                CheckResult(
                    name="SOUL.md content linter (UUIDs)",
                    status=CheckStatus.PASS,
                    message="No UUID scoping patterns found in SOUL.md",
                )
            )
        if SOUL_SCOPING_PREFIXES.search(content):
            results.append(
                CheckResult(
                    name="SOUL.md content linter (scoping prefixes)",
                    status=CheckStatus.WARN,
                    message="SOUL.md contains lines starting with repo:, branch:, or project_id:",
                    fix_hint=(
                        "Move scoping rules to pre_filter.py. "
                        "SOUL.md should contain priority/action rules only."
                    ),
                )
            )
        else:
            results.append(
                CheckResult(
                    name="SOUL.md content linter (scoping prefixes)",
                    status=CheckStatus.PASS,
                    message="No scoping prefix patterns found in SOUL.md",
                )
            )
        return results

    def _check_require_signatures_advisory(self, config: GatewayConfig) -> list[CheckResult]:
        has_secrets = bool(config.watch.linear.secret or config.watch.github.secret)
        if not config.require_signatures and has_secrets:
            return [
                CheckResult(
                    name="Signature enforcement",
                    status=CheckStatus.WARN,
                    message=(
                        "HMAC secrets are configured but GATEWAY_REQUIRE_SIGNATURES=false — "
                        "signatures are validated when present but not required"
                    ),
                    fix_hint="",  # Advisory only — no action required
                )
            ]
        return []

    def print_results(self, results: list[CheckResult]) -> None:
        """Render results to terminal using rich."""
        table = Table(box=box.SIMPLE, show_header=False, padding=(0, 1))
        table.add_column("status", style="bold", width=6)
        table.add_column("name")
        table.add_column("message")

        failures = 0
        warnings = 0
        for r in results:
            if r.status == CheckStatus.FAIL:
                failures += 1
                table.add_row("[red][FAIL][/red]", r.name, r.message)
                if r.fix_hint:
                    table.add_row("", "", f"[dim]Fix: {r.fix_hint}[/dim]")
            elif r.status == CheckStatus.WARN:
                warnings += 1
                table.add_row("[yellow][WARN][/yellow]", r.name, r.message)
                if r.fix_hint:
                    table.add_row("", "", f"[dim]Fix: {r.fix_hint}[/dim]")
            elif self.verbose:
                table.add_row("[green][ OK ][/green]", r.name, r.message)

        _console.print(table)
        passed = len(results) - failures - warnings
        _console.print(f"{passed} passed, {warnings} warned, {failures} failed")


@click.command("doctor")
@click.option("--verbose", is_flag=True, help="Show all checks including passing ones.")
@click.option(
    "--env-file",
    type=click.Path(exists=True),
    default=None,
    help="Path to .env file to load before checking config.",
)
def doctor(verbose: bool, env_file: str | None) -> None:
    """Run pre-flight config checks and report health status."""
    if env_file:
        from dotenv import load_dotenv

        load_dotenv(env_file, override=True)

    runner = DoctorRunner(verbose=verbose)
    results = runner.run()
    runner.print_results(results)
    failed = [r for r in results if r.status == CheckStatus.FAIL]
    raise SystemExit(1 if failed else 0)
