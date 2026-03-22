FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy source
COPY heartbeat_gateway/ ./heartbeat_gateway/

# Create non-root user and workspace directory
RUN useradd -m -u 1000 agent && \
    mkdir -p /workspace && \
    chown -R agent:agent /workspace /app

# Declare workspace as named volume
VOLUME ["/workspace"]

# Switch to non-root user
USER agent

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "heartbeat_gateway.app:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8080"]
