# Lab 06 Recreate - Production Agent

This folder is a clean Lab 06 rebuild with all required deliverables.

## Included Files

- app/main.py
- app/config.py
- app/auth.py
- app/rate_limiter.py
- app/cost_guard.py
- utils/mock_llm.py
- Dockerfile (multi-stage)
- docker-compose.yml (agent + redis)
- requirements.txt
- .env.example
- .dockerignore
- railway.toml

## Features

- API key authentication (`X-API-Key`)
- Rate limiting (`10 req/min` per user)
- Cost guard (`$10/month` per user)
- Health check (`/health`)
- Readiness check (`/ready`)
- Graceful shutdown (`SIGTERM` handling)
- Stateless design with Redis-backed history
- No hardcoded secrets in source code

## Run Locally

```bash
cd 06-lab-complete-recreate
docker compose up --build
```

API test:

```bash
curl -X POST http://localhost:8000/ask \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"test","question":"Hello"}'
```

## Deploy

Railway config is provided in `railway.toml`.
Set environment variables from `.env.example` in Railway dashboard.
