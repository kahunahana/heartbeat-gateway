"""gateway init — interactive .env configuration wizard.

CONSTRAINT: Do NOT import from heartbeat_gateway.app. Do NOT import from
heartbeat_gateway.commands.doctor. Import only from
heartbeat_gateway.config.schema if env var names are needed.
"""

import click


@click.command("init")
def init() -> None:
    """Interactive wizard to configure .env for heartbeat-gateway."""
    raise NotImplementedError("gateway init not yet implemented")
