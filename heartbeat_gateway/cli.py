import click


@click.group(invoke_without_command=True)
@click.pass_context
def cli(ctx: click.Context) -> None:
    """heartbeat-gateway — event-driven webhook gateway for AI agents."""
    if ctx.invoked_subcommand is None:
        ctx.invoke(serve)


@cli.command()
def serve() -> None:
    """Start the uvicorn server (default when no subcommand given)."""
    import uvicorn

    uvicorn.run("heartbeat_gateway.app:create_app", factory=True, host="0.0.0.0", port=8080)


from heartbeat_gateway.commands.doctor import doctor  # noqa: E402

cli.add_command(doctor)

from heartbeat_gateway.commands.init import init  # noqa: E402

cli.add_command(init)
