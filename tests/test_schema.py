"""Schema regression tests — GatewayConfig env var loading for new adapter WatchConfig classes.

CONSTRAINT: monkeypatch.setenv only. Never mock GatewayConfig. Instantiate real GatewayConfig().
"""

from heartbeat_gateway.config.schema import GatewayConfig


def test_amplitude_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("GATEWAY_WATCH__AMPLITUDE__SECRET", "amp-secret-xyz")
    config = GatewayConfig()
    assert config.watch.amplitude.secret == "amp-secret-xyz"


def test_braintrust_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("GATEWAY_WATCH__BRAINTRUST__SECRET", "btst-secret-xyz")
    config = GatewayConfig()
    assert config.watch.braintrust.secret == "btst-secret-xyz"


def test_langsmith_config_loads_from_env(monkeypatch):
    monkeypatch.setenv("GATEWAY_WATCH__LANGSMITH__TOKEN", "ls-token-xyz")
    config = GatewayConfig()
    assert config.watch.langsmith.token == "ls-token-xyz"
