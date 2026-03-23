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

## Persistent Cloudflare Tunnel (recommended for VPS)

Linear and PostHog require HTTPS. The cleanest production solution for a VPS deployment is a named Cloudflare Tunnel — free, persistent across reboots, no domain certificate management required. If your domain is on Cloudflare you get a clean subdomain (e.g. `hooks.yourdomain.com`).

### Prerequisites

- A Cloudflare account
- Your domain's nameservers pointed at Cloudflare (free plan is sufficient)
- `cloudflared` installed on the VPS

```bash
# Install cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
  -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared

cloudflared --version
```

### Step 1 — Authenticate to Cloudflare

```bash
cloudflared tunnel login
```

This prints a URL. Open it in a browser, select your domain, and authorize. A `cert.pem` is saved to `~/.cloudflared/cert.pem` automatically once you authorize.

### Step 2 — Create the named tunnel

```bash
cloudflared tunnel create heartbeat-gateway
```

Note the UUID printed — you need it in the next step. It looks like `a1b2c3d4-xxxx-xxxx-xxxx-xxxxxxxxxxxx`.

### Step 3 — Write the config file

```bash
mkdir -p ~/.cloudflared
cat > ~/.cloudflared/config.yml << 'EOF'
tunnel: heartbeat-gateway
credentials-file: /root/.cloudflared/<YOUR-TUNNEL-UUID>.json

ingress:
  - hostname: hooks.yourdomain.com
    service: http://localhost:8080
  - service: http_status:404
EOF
```

Replace `<YOUR-TUNNEL-UUID>` with the UUID from Step 2, and `hooks.yourdomain.com` with your chosen subdomain.

### Step 4 — Create the DNS record

```bash
cloudflared tunnel route dns heartbeat-gateway hooks.yourdomain.com
```

This creates the CNAME record in Cloudflare DNS automatically — no manual dashboard editing needed.

### Step 5 — Install as a systemd service

```bash
cloudflared service install
systemctl enable cloudflared
systemctl start cloudflared
systemctl status cloudflared
```

The tunnel now starts automatically on boot.

### Step 6 — Verify

```bash
curl https://hooks.yourdomain.com/health
# → {"status":"ok","version":"0.1.1"}
```

### Step 7 — Update webhook URLs

| Source  | URL |
|---------|-----|
| GitHub  | `https://hooks.yourdomain.com/webhooks/github` |
| Linear  | `https://hooks.yourdomain.com/webhooks/linear` |
| PostHog | `https://hooks.yourdomain.com/webhooks/posthog` |

### Local development (temporary tunnel)

For local dev only — not suitable for production as the URL changes on every restart:

```bash
# ngrok
ngrok http 8080

# Cloudflare quick tunnel (temporary URL)
cloudflared tunnel --url http://localhost:8080
```

---

## Health Check

All deployment platforms should check:

```
GET /health
→ {"status": "ok", "version": "0.1.1"}
```

Configure your load balancer or platform health check to hit `/health` every 30 seconds.
