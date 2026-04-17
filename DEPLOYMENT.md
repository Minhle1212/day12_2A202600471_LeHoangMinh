# Deployment Information

## Project
`06-lab-complete-recreate`

## Public URL
https://day122a202600471lehoangminh-production.up.railway.app

## Platform
Railway (recommended) or Render

## Local Verification (Completed)

### Build and start
```bash
cd 06-lab-complete-recreate
docker compose up -d --build
```

### Health Check (Public)
```bash
curl https://day122a202600471lehoangminh-production.up.railway.app/health
```
Observed output:
```json
{"status":"ok","instance_id":"68d45a975f83","uptime_seconds":136.2,"redis_connected":true,"timestamp":"2026-04-17T16:49:11.717702+00:00"}
```

### API Test (Public, with authentication)
```bash
curl -X POST https://day122a202600471lehoangminh-production.up.railway.app/ask \
  -H "X-API-Key: dev-secret-key" \
  -H "Content-Type: application/json" \
  -d '{"user_id":"public-test","question":"hello redis"}'
```
Observed output:
```json
{"user_id":"public-test","question":"hello redis","answer":"Redis stores fast shared state across instances for stateless scaling.","served_by":"68d45a975f83","usage":{"rate_limit_remaining":9,"monthly_spend_usd":0.000013,"monthly_budget_usd":10.0},"timestamp":"2026-04-17T16:49:12.276217+00:00"}
```

### Readiness Checker
```bash
python check_production_ready.py
```
Observed output: `19/19 checks passed`

## Environment Variables Required
- `PORT`
- `REDIS_URL`
- `AGENT_API_KEY`
- `LOG_LEVEL`
- `RATE_LIMIT_PER_MINUTE`
- `MONTHLY_BUDGET_USD`

## Deployment Steps (Railway)

```bash
cd 06-lab-complete-recreate
railway init
railway variables set PORT=8000
railway variables set REDIS_URL=<your_railway_redis_url>
railway variables set AGENT_API_KEY=<your_secret_key>
railway variables set LOG_LEVEL=INFO
railway variables set RATE_LIMIT_PER_MINUTE=10
railway variables set MONTHLY_BUDGET_USD=10.0
railway up
railway domain
```

screenshots of the deployed service in D:\AI\day12_2A202600471_LeHoangMinh\screenshot\Screenshot 2026-04-17 235752.png
