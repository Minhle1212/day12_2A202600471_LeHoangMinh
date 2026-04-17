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

1. **Base image:** `python:3.11-slim` — lightweight Python 3.11 image
2. **Working directory:** `/app`
3. **Why `COPY requirements.txt` first?** — Docker caches layers. If only code changed but dependencies didn't, Docker reuses the cached dependency layer, speeding up builds significantly.
4. **CMD vs ENTRYPOINT:**
   - `CMD` — Default command that can be overridden at runtime
   - `ENTRYPOINT` — Hardcoded command; arguments passed at runtime are appended
   - `CMD` is more flexible; `ENTRYPOINT` is for fixed command patterns

### Exercise 2.3: Image size comparison

- **Develop image:** `python:3.11-slim` base (~150 MB) + dependencies + all code
- **Production image:** Multi-stage build — builder stage (full Python + build tools) discarded, only runtime stage copied (~45-80 MB)
- **Difference:** ~50-70% smaller with multi-stage build

---

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment

- **URL:** https://your-app.railway.app
- **Screenshot:** [Link to screenshot in repo]

### Exercise 3.2: render.yaml vs railway.toml differences

- **railway.toml** — Railway's native config, deploys directly via Railway CLI (`railway up`)
- **render.yaml** — Render's Blueprint format, used for GitHub-connected auto-deployments via Render dashboard

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
1. Client POSTs username/password to `/token`
2. Server validates and returns a signed JWT token
3. Client includes `Authorization: Bearer <token>` header in subsequent requests
4. Server verifies token signature and expiry before processing

### Exercise 4.3: Rate Limiting

Code analyzed: `04-api-gateway/production/rate_limiter.py`

- Algorithm: Sliding window (uses Redis sorted sets)
- Limit: 10 requests per minute per user
- Admin bypass: Configurable via `ADMIN_USER_IDS` environment variable

### Exercise 4.4: Cost Guard Implementation

Code analyzed: `04-api-gateway/production/cost_guard.py`

Approach:
- Each user has a monthly budget (default $10/month)
- Track spending in Redis with key format: `budget:{user_id}:{YYYY-MM}`
- Before processing a request, check if `current_spending + estimated_cost <= budget`
- If exceeded → return `402 Payment Required`
- Reset spending tracking at the start of each month (TTL on Redis keys)

---

## Part 5: Scaling & Reliability

### Exercise 5.1: Health Checks

Code analyzed: `05-scaling-reliability/develop/app.py`

- `/health` (liveness probe) — Returns `200 OK` if the process is alive. Simple status check.
- `/ready` (readiness probe) — Checks Redis and database connectivity. Returns `200 OK` if ready, `503 Service Unavailable` otherwise. Load balancers use this to decide whether to route traffic.

### Exercise 5.2: Graceful Shutdown

Code analyzed: `05-scaling-reliability/production/app.py`

Implementation:
1. Register `SIGTERM` signal handler
2. On SIGTERM: Set `is_ready = False` to stop new traffic
3. Wait for in-flight requests to complete (via lifespan shutdown hook)
4. Close database/Redis connections
5. Exit cleanly

### Exercise 5.3: Stateless Design

Code analyzed: `05-scaling-reliability/production/app.py`

**Anti-pattern (stateful):**
```python
conversation_history = {}  # Stored in memory — lost on restart or different instance
```

**Correct (stateless):**
```python
# Conversation history stored in Redis
history = r.lrange(f"history:{user_id}", 0, -1)
r.rpush(f"history:{user_id}", new_turn)
```

Why? When scaling to multiple instances, each has its own memory. User's request might hit instance 1 (stores history there), then next request hits instance 2 (has no history). Redis is shared across all instances.

### Exercise 5.4: Load Balancing

Code analyzed: `05-scaling-reliability/production/nginx.conf` + `docker-compose.yml`

- Nginx distributes incoming requests across multiple agent instances using round-robin by default
- With `--scale agent=3`, 3 agent containers run behind the load balancer
- If one instance dies, Nginx stops routing to it automatically
- Requests are spread evenly; each instance can serve any user because state is in Redis

### Exercise 5.5: Stateless Test Results

Test script: `05-scaling-reliability/production/test_stateless.py`

Expected results:
- Create a conversation with user A on instance 1
- Kill instance 1
- User A's next request → routed to instance 2 or 3
- Conversation history preserved in Redis → **CONTINUES seamlessly**

---

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
