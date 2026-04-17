# Day 12 Lab - Mission Answers

> **Student Name:** Le Hoang Minh
> **Student ID:** 2A202600471
> **Date:** 17/4/2026

---

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found

Code analyzed: `01-localhost-vs-production/develop/app.py`

**5+ Anti-patterns identified:**

1. **Hardcoded API Key** — `OPENAI_API_KEY = "sk-hardcoded-fake-key..."` is in plain text in the code. If pushed to GitHub, the secret is exposed immediately.
2. **Hardcoded Database Password** — `DATABASE_URL = "postgresql://admin:password123@localhost:5432/mydb"` contains credentials in the code.
3. **Hardcoded Config Values** — `DEBUG = True`, `MAX_TOKENS = 500` are fixed values. Cannot change them without editing code.
4. **Print Statements Instead of Logging** — Using `print()` for debugging (`print(f"[DEBUG] Got question: {question}")`). Cannot filter by log level, cannot send to log aggregator.
5. **Logging Secrets to Output** — `print(f"[DEBUG] Using key: {OPENAI_API_KEY}")` prints the secret key to stdout.
6. **No Health Check Endpoint** — No `/health` or `/ready` endpoint. If the agent crashes, the cloud platform has no way to detect it to restart.
7. **Fixed Port** — `port=8000` is hardcoded. Railway/Render inject `PORT` via environment variable; the app ignores it.
8. **Localhost Binding** — `host="localhost"` means only connections from the same machine work. In a container/cloud, the app must bind to `0.0.0.0`.
9. **Debug Reload in Production** — `reload=True` in uvicorn causes the server to restart on file changes. This is dangerous and resource-heavy in production.

### Exercise 1.3: Comparison table

| Feature | Develop (`basic/`) | Production (`advanced/`) | Why Important? |
|---------|-------------------|------------------------|---------------|
| Config | Hardcoded values (`DEBUG=True`) | Environment variables via `Settings` class | Change behavior without code changes; different config per environment |
| Secrets | Plain text in code (`OPENAI_API_KEY="sk-..."`) | Read from env vars, never in code | Secrets stay safe even if repo is public |
| Logging | `print()` statements | Structured JSON logging via `logging` module | Structured logs parseable by Datadog/Loki; log levels filterable |
| Health Check | None | `/health` + `/ready` endpoints | Platform detects crashes and routes traffic away from unhealthy instances |
| Port | Hardcoded `8000` | From `PORT` env var | Railway/Render inject PORT dynamically |
| Host Binding | `localhost` | `0.0.0.0` | Required to accept external connections in containers |
| Shutdown | Sudden (Ctrl+C) | Graceful via `lifespan` + `SIGTERM` handler | In-flight requests complete before shutdown |
| Reload | `reload=True` always | `reload=settings.debug` (only in dev) | Prevents unintended restarts in production |
| CORS | None | Configured via `ALLOWED_ORIGINS` | Prevents unauthorized cross-origin requests |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions

Code analyzed: `02-docker/develop/Dockerfile`

1. **Base image:** `python:3.11` (full Python image) in develop Dockerfile
2. **Working directory:** `/app`
3. **Why `COPY requirements.txt` first?** — Docker caches layers. If only code changed but dependencies didn't, Docker reuses the cached dependency layer, speeding up builds significantly.
4. **CMD vs ENTRYPOINT:**
   - `CMD` — Default command that can be overridden at runtime
   - `ENTRYPOINT` — Hardcoded command; arguments passed at runtime are appended
   - `CMD` is more flexible; `ENTRYPOINT` is for fixed command patterns

### Exercise 2.2: Build and run results

Commands executed from project root:

```bash
docker build -f 02-docker/develop/Dockerfile -t my-agent:develop .
docker run -p 8001:8000 my-agent:develop
curl http://localhost:8001/health
curl -X POST --get --data-urlencode "question=What is Docker?" http://localhost:8001/ask
docker images my-agent:develop
```

Observed outputs:

- Health endpoint: `{"status":"ok","uptime_seconds":5.6,"container":true}`
- Ask endpoint: `{"answer":"Container là cách đóng gói app để chạy ở mọi nơi. Build once, run anywhere!"}`
- Image size: `my-agent:develop 1.66GB`

### Exercise 2.3: Image size comparison

- **Develop image:** `python:3.11` base + dependencies + all code = `1.66GB`
- **Production image:** Multi-stage build — builder stage (full Python + build tools) discarded, only runtime stage copied (236MB)
- **Difference:** from `1.66GB` to `236MB` (about `85.8%` smaller)

### Exercise 2.4: Docker Compose stack

Stack run in `02-docker/production` with compose:

```bash
docker compose up -d
docker compose ps
curl http://127.0.0.1/health
```

Services started:

- `agent` (FastAPI app)
- `redis` (cache/session)
- `qdrant` (vector DB)
- `nginx` (reverse proxy)

Communication flow:

- Client → `nginx:80`
- Nginx proxies to `agent:8000`
- Agent talks to `redis:6379` and `qdrant:6333`

Observed health output:

- `{"status":"ok","uptime_seconds":217.1,"version":"2.0.0","timestamp":"2026-04-17T09:54:19.578852"}`

Observed ask output (tested via WSL request to avoid Windows IIS localhost conflict):

- `{"answer":"Tôi là AI agent được deploy lên cloud. Câu hỏi của bạn đã được nhận."}`

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **URL:** https://day122a202600471lehoangminh-production.up.railway.app
- **Deploy command used:** `railway up`
- **Variables set:** `PORT=8000`
- **Screenshot**: D:\AI\day12_2A202600471_LeHoangMinh\screenshot\image.png, D:\AI\day12_2A202600471_LeHoangMinh\screenshot\Screenshot 2026-04-17 171611.png

Verification tests:

```bash
curl https://day122a202600471lehoangminh-production.up.railway.app/health
```

Observed output:

- `{"status":"ok","uptime_seconds":132.7,"platform":"Railway","timestamp":"2026-04-17T10:09:32.920329+00:00"}`

Ask endpoint test (PowerShell JSON body):

```powershell
$body = @{ question = "Hello" } | ConvertTo-Json
Invoke-RestMethod -Uri "https://day122a202600471lehoangminh-production.up.railway.app/ask" -Method Post -ContentType "application/json" -Body $body
```

Observed output:

- JSON response includes `question`, `answer`, and `platform="Railway"`

Note:

- `railway logs` initially returned "No service could be found" because CLI context had no selected service. Fix by running `railway service` first, then `railway logs`.

### Exercise 3.2: render.yaml vs railway.toml differences

Files compared:

- `03-cloud-deployment/railway/railway.toml`
- `03-cloud-deployment/render/render.yaml`

| Aspect | `railway.toml` | `render.yaml` |
|--------|----------------|---------------|
| Platform scope | Chỉ cho Railway | Chỉ cho Render |
| Deploy workflow | CLI-first (`railway up`) | GitHub Blueprint-first (Dashboard auto-provision) |
| Build definition | `[build] builder = "NIXPACKS"` (auto buildpack detection) | `runtime: python` + explicit `buildCommand` |
| Start command | `[deploy].startCommand` | `startCommand` per service |
| Health check | `healthcheckPath`, `healthcheckTimeout` | `healthCheckPath` |
| Restart policy | `restartPolicyType`, `restartPolicyMaxRetries` | Managed by Render service lifecycle (no direct same fields here) |
| Environment vars | Set mainly via CLI/Dashboard (`railway variables set ...`) | Defined under `envVars`, supports `sync: false` and `generateValue: true` |
| Multi-service support | One service config per linked Railway service | Native multi-service blueprint in one file (`web` + `redis`) |
| Infra as code style | App-focused deploy settings | Full infrastructure blueprint (region, plan, services, Redis add-on) |

Conclusion:

- `railway.toml` is lightweight and optimized for fast CLI deployment.
- `render.yaml` is more explicit and infrastructure-oriented, suitable when provisioning multiple managed services in one declarative file.

---

## Part 4: API Security

### Exercise 4.1: API Key Authentication

Code analyzed: `04-api-gateway/develop/app.py`

- API key checked via `X-API-Key` header against the `AGENT_API_KEY` env var
- Missing or wrong key → `401 Unauthorized`
- Rotate key by changing the `AGENT_API_KEY` environment variable

### Exercise 4.2: JWT Authentication (Advanced)

Code analyzed: `04-api-gateway/production/auth.py`

JWT flow:
1. Client POSTs username/password to `/auth/token`
2. Server validates credentials via `authenticate_user()` against `DEMO_USERS`
3. Server returns JWT signed with `HS256` (`JWT_SECRET`) and `exp` = 60 minutes
4. Client includes `Authorization: Bearer <token>` header for protected routes (e.g., `/ask`, `/me/usage`, `/admin/stats`)
5. Server verifies signature/expiry in `verify_token()` and extracts `username` + `role`

### Exercise 4.3: Rate Limiting

Code analyzed: `04-api-gateway/production/rate_limiter.py`

- Algorithm: Sliding Window Counter using in-memory `deque` per user
- Storage: In-memory dictionary (`defaultdict(deque)`), not Redis
- Limits:
   - User role: `10 requests / 60 seconds`
   - Admin role: `100 requests / 60 seconds`
- On limit exceeded: returns `429 Too Many Requests` with headers:
   - `X-RateLimit-Limit`
   - `X-RateLimit-Remaining`
   - `X-RateLimit-Reset`
   - `Retry-After`

### Exercise 4.4: Cost Guard Implementation

Code analyzed: `04-api-gateway/production/cost_guard.py`

Approach:
- In-memory cost tracking with `UsageRecord` (per user, per day)
- Budget model:
   - Per-user daily budget: `$1.0/day`
   - Global daily budget: `$10.0/day`
- `check_budget(user_id)` is called before LLM execution:
   - If user exceeds per-user daily budget → `402 Payment Required`
   - If system exceeds global budget → `503 Service Unavailable`
- `record_usage(user_id, input_tokens, output_tokens)` updates token counts and cost after each request
- Cost is estimated from token pricing constants (`PRICE_PER_1K_INPUT_TOKENS`, `PRICE_PER_1K_OUTPUT_TOKENS`)

### Section 4 Evidence (Executed Tests)

Develop server (`04-api-gateway/develop`, port `8002`):

- `POST /ask` without `X-API-Key` → `401`
- `POST /ask` with wrong `X-API-Key` → `403`
- `POST /ask` with correct `X-API-Key: secret-key-123` → `200` + answer JSON

Production server (`04-api-gateway/production`, port `8003`):

- `POST /auth/token` with `student/demo123` → `200` + JWT token
- `POST /ask` with valid Bearer token → `200`
- Rate-limit stress test (12 requests as student) returned:
   - `RATE_STATUSES = [200, 200, 200, 200, 200, 200, 200, 200, 200, 429, 429, 429]`

Implementation note during testing:

- Fixed middleware bug in `04-api-gateway/production/app.py`:
   - Replaced invalid `response.headers.pop("server", None)`
   - With safe deletion using `if "server" in response.headers: del response.headers["server"]`
   - This resolved `500 Internal Server Error` responses in production tests.

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health Checks

Code analyzed: `05-scaling-reliability/develop/app.py`

- `/health` (liveness probe) — returns process/runtime status, uptime, environment, and basic dependency checks.
- `/ready` (readiness probe) — checks internal readiness state (`_is_ready`) and returns `503` while starting or shutting down.

Verified in scaled production stack via Nginx (`http://localhost:8080`):

- `GET /health` → `{"status":"ok","instance_id":"instance-8c1940","uptime_seconds":19.6,"storage":"redis","redis_connected":true}`
- `GET /ready` → `{"ready":true,"instance":"instance-8c1940"}`

### Exercise 5.2: Graceful Shutdown

Code analyzed: `05-scaling-reliability/production/app.py`

Implementation:
1. Register `SIGTERM` signal handler
2. On SIGTERM: set `_is_shutting_down = True` and `_is_ready = False` so `/ready` starts returning `503`
3. Track in-flight requests via middleware counter
4. During shutdown lifespan: wait (up to 30s) for in-flight requests to finish
5. Exit cleanly (`uvicorn` with `timeout_graceful_shutdown=30`)

### Exercise 5.3: Stateless Design

Code analyzed: `05-scaling-reliability/production/app.py`

Implemented stateless session storage with Redis only:

- Session save/load through Redis keys (`session:<session_id>`)
- Conversation history appended to Redis-backed session
- No in-memory fallback in production path (Redis is required)

Why this is correct: with multiple replicas, any instance can continue the same conversation because state is centralized in Redis.

### Exercise 5.4: Load Balancing

Code analyzed: `05-scaling-reliability/production/nginx.conf` + `docker-compose.yml`

Stack and verification commands:

```bash
docker compose up -d --build --scale agent=3
docker compose ps
python test_stateless.py
```

Observed service state:

- `production-agent-1`, `production-agent-2`, `production-agent-3` all running (healthy)
- `production-nginx-1` exposing `0.0.0.0:8080->80`
- `production-redis-1` healthy

Observed load balancing evidence from test output:

- `Instances used: {'instance-716d96', 'instance-8c1940', 'instance-449099'}` (3 distinct replicas served requests)

### Exercise 5.5: Stateless Test Results

Test script: `05-scaling-reliability/production/test_stateless.py`

Verified results (normal scaled run):

- Total requests: `5`
- Instances used: `{'instance-716d96', 'instance-8c1940', 'instance-449099'}`
- Conversation history count: `10` messages
- Final status: `Session history preserved across all instances via Redis`

Additional resilience test (after stopping one replica):

```bash
docker stop production-agent-1
python test_stateless.py
```

Observed after failure:

- Requests still succeeded via remaining replicas (`instance-716d96`, `instance-449099`)
- Conversation history still preserved (`10` messages)
- Conclusion: service continued correctly with one instance down.

---

## Part 6: Final Project (Lab 06 Recreate)

### Objective

Built a new clean production-ready project in:

- `06-lab-complete-recreate/`

This project implements the required structure and production features from Day 12 Lab.

### Final project structure delivered

```text
06-lab-complete-recreate/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── auth.py
│   ├── rate_limiter.py
│   └── cost_guard.py
├── utils/
│   └── mock_llm.py
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── .env.example
├── .dockerignore
├── railway.toml
├── check_production_ready.py
└── README.md
```

### Implemented requirements

Functional:

- Agent answers questions via REST API (`POST /ask`)
- Conversation state stored in Redis per user (`history:<user_id>`)

Non-functional:

- Multi-stage Docker build
- Configuration via environment variables
- API key authentication (`X-API-Key`)
- Rate limiting (`10 req/min`)
- Cost guard (`$10/month` per user)
- Health check (`GET /health`)
- Readiness check (`GET /ready`)
- Graceful shutdown with SIGTERM handling
- Stateless design using Redis
- Structured JSON logging
- No hardcoded secrets in source

### Validation results

Deployed public URL:

- `https://day122a202600471lehoangminh-production.up.railway.app`

Readiness checker:

```bash
cd 06-lab-complete-recreate
python check_production_ready.py
```

Observed result:

- `19/19 checks passed`

Runtime verification with Docker Compose:

```bash
docker compose up -d --build
```

Observed `GET /health` response:

```json
{"status":"ok","instance_id":"b10fc11f1b9c","uptime_seconds":3.4,"redis_connected":true,"timestamp":"2026-04-17T16:36:33.948910+00:00"}
```

Observed authenticated `POST /ask` response:

```json
{"user_id":"test","question":"hello redis","answer":"Redis stores fast shared state across instances for stateless scaling.","served_by":"b10fc11f1b9c","usage":{"rate_limit_remaining":9,"monthly_spend_usd":0.000013,"monthly_budget_usd":10.0},"timestamp":"2026-04-17T16:36:34.116816+00:00"}
```

Stack shutdown:

```bash
docker compose down
```

Deployment notes for this recreated project are documented in `DEPLOYMENT.md`.

Public endpoint verification (after deployment):

- `GET /health` on public URL returned:
   - `{"status":"ok","instance_id":"68d45a975f83","uptime_seconds":136.2,"redis_connected":true,"timestamp":"2026-04-17T16:49:11.717702+00:00"}`
- Authenticated `POST /ask` on public URL returned:
   - `{"user_id":"public-test","question":"hello redis","answer":"Redis stores fast shared state across instances for stateless scaling.","served_by":"68d45a975f83","usage":{"rate_limit_remaining":9,"monthly_spend_usd":0.000013,"monthly_budget_usd":10.0},"timestamp":"2026-04-17T16:49:12.276217+00:00"}`

## Pre-Submission Checklist

- [ ] Repository is public (or instructor has access)
- [ ] `MISSION_ANSWERS.md` completed with all exercises
- [ ] `DEPLOYMENT.md` has working public URL
- [ ] All source code in `app/` directory
- [ ] `README.md` has clear setup instructions
- [ ] No `.env` file committed (only `.env.example`)
- [ ] No hardcoded secrets in code
- [ ] Public URL is accessible and working
- [ ] Screenshots included in `screenshots/` folder
- [ ] Repository has clear commit history
