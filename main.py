"""
Development convenience runner.

    python main.py

For production, prefer the installed script:

    heartbeat-gateway

Or uvicorn directly:

    uv run uvicorn heartbeat_gateway.app:create_app --factory --host 0.0.0.0 --port 8080
"""
from heartbeat_gateway.app import main

if __name__ == "__main__":
    main()
