from heartbeat_gateway.config.schema import GatewayConfig


def load_config() -> GatewayConfig:
    """Load configuration from environment variables."""
    return GatewayConfig()
