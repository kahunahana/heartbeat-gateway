# Deploying heartbeat-gateway

---

## Bare-Metal (uvicorn)

The simplest deployment — runs wherever Python 3.11+ and `uv` are available.

### Prerequisites

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/kahunahana/heartbeat-gateway
cd heartbeat-gateway
uv sync
```

### Configure

```bash
cp .env.example .env  # edit with your keys
# Ensure SOUL.md exists at GATEWAY_SOUL_MD_PATH
```

### Run

```bash
uv run uvicorn heartbeat_gateway.app:create_app \
  --factory \
  --host 0.0.0.0 \
  --port 8080
```

### Run as a systemd service (Linux)

```ini
# /etc/systemd/system/heartbeat-gateway.service
[Unit]
Description=heartbeat-gateway webhook service
After=network.target

[Service]
Type=simple
User=agent
WorkingDirectory=/opt/heartbeat-gateway
EnvironmentFile=/opt/heartbeat-gateway/.env
ExecStart=/home/agent/.local/bin/uv run uvicorn heartbeat_gateway.app:create_app \
  --factory --host 0.0.0.0 --port 8080
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable heartbeat-gateway
sudo systemctl start heartbeat-gateway
```

---

## Docker

### Dockerfile

```dockerfile
FROM python:3.11-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app

# Install dependencies (cached layer)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

# Copy source
COPY heartbeat_gateway/ ./heartbeat_gateway/

EXPOSE 8080

CMD ["uv", "run", "uvicorn", "heartbeat_gateway.app:create_app", \
     "--factory", "--host", "0.0.0.0", "--port", "8080"]
```

### Build and run

```bash
docker build -t heartbeat-gateway .

docker run -d \
  --name heartbeat-gateway \
  -p 8080:8080 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e GATEWAY_WORKSPACE_PATH=/workspace \
  -e GATEWAY_SOUL_MD_PATH=/workspace/SOUL.md \
  -v /path/to/your/workspace:/workspace \
  heartbeat-gateway
```

Mount your workspace directory so `HEARTBEAT.md`, `SOUL.md`, and `audit.log` persist across container restarts.

### docker-compose.yml

```yaml
services:
  heartbeat-gateway:
    build: .
    ports:
      - "8080:8080"
    env_file: .env
    volumes:
      - ./workspace:/workspace
    restart: unless-stopped
```

```bash
docker compose up -d
```

---

## Railway

Railway detects Python projects and deploys automatically.

1. Push your repo to GitHub
2. In Railway: **New Project** → **Deploy from GitHub repo** → select `heartbeat-gateway`
3. Set environment variables in Railway's **Variables** tab:

```
ANTHROPIC_API_KEY=sk-ant-...
GATEWAY_WORKSPACE_PATH=/data/workspace
GATEWAY_SOUL_MD_PATH=/data/workspace/SOUL.md
```

4. Add a **Volume** mounted at `/data/workspace` so HEARTBEAT.md persists across deploys
5. Set the start command in `railway.toml`:

```toml
[deploy]
startCommand = "uvicorn heartbeat_gateway.app:create_app --factory --host 0.0.0.0 --port $PORT"
```

Railway sets `$PORT` automatically.

---

## Render

1. Push your repo to GitHub
2. In Render: **New** → **Web Service** → connect your repo
3. Configure:
   - **Runtime:** Python 3
   - **Build command:** `pip install uv && uv sync`
   - **Start command:** `uv run uvicorn heartbeat_gateway.app:create_app --factory --host 0.0.0.0 --port $PORT`
4. Add environment variables in the **Environment** tab
5. Add a **Persistent Disk** mounted at `/data/workspace` for HEARTBEAT.md

---

## Exposing to the Public Internet (Development)

For local development, use a tunnel to receive webhooks:

```bash
# ngrok
ngrok http 8080
# → https://abc123.ngrok.io

# Cloudflare Tunnel (free, persistent URL)
cloudflared tunnel --url http://localhost:8080
```

Use the tunnel URL as your webhook URL in Linear/GitHub/PostHog settings.

---

## Health Check

All deployment platforms should check:

```
GET /health
→ {"status": "ok", "version": "0.1.0"}
```

Configure your load balancer or platform health check to hit `/health` every 30 seconds.
