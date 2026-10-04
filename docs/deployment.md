# Deployment & Operations Guide — Farmer Decision Support System

This document provides a comprehensive, production-ready operational guide for deploying, configuring, securing, and maintaining the **Farmer Decision Support System**.

---

## 1. Overview & System Architecture

The Farmer Decision Support System is an end-to-end agricultural decision engine providing:
- **Core Domain Entities:** Farmer, Farm, and Crop parcel tracking.
- **Empirical Observation Store:** Crop health/stages, farm weather, and mandi market prices.
- **Provider-Independent Ingestion:** Open-Meteo REST adapter for automated weather tracking and official Government of India Open Government Data (`data.gov.in`) adapter for APMC mandi commodity rates.
- **Deterministic Indicator Service:** 14-day rolling weather metrics, crop health aggregations, and market price trends.
- **Transparent Decision Engine:** Rule-based harvest and sell readiness assessments (zero black-box ML for critical decisions).
- **Market Price Prediction Service:** Scikit-learn Ridge regression baseline with confidence intervals.
- **AI Explanation Layer:** Structured, rule-driven, farmer-friendly explanations.
- **Harvest & Sell Recommendation Engines:** Separate, transparent harvest timing and market action recommendations.

### Architecture Overview

```text
       [ Web Browser / Mobile Clients ]
                      │
                      ▼
         [ Nginx Reverse Proxy / SSL ]
          │                         │
     Static Assets            /api Traffic
          │                         │
          ▼                         ▼
   [ Built SPA Frontend ]     [ FastAPI Backend (Uvicorn) ]
   (HTML / JS / Tailwind)     (Settings, Auth/CORS, Services)
                                    │
                         ┌──────────┴──────────┐
                         ▼                     ▼
                  [ Primary Database ]   [ External Adapters ]
                  (SQLite / PostgreSQL)  - Open-Meteo Weather
                                         - GoI data.gov.in OGD
```

---

## 2. Prerequisites & System Requirements

### Hardware Requirements
- **Minimum:** 1 vCPU, 1 GB RAM, 10 GB SSD disk.
- **Recommended (Production):** 2 vCPUs, 4 GB RAM, 25 GB SSD disk.

### Software Requirements
- **Operating System:** Linux (Ubuntu 22.04 LTS / Debian 12 / RHEL 9) or Windows Server.
- **Python:** Python 3.10 or higher.
- **Node.js:** Node.js v18.x or v20.x LTS with `npm`.
- **Database (choose one):**
  - **SQLite:** Pre-installed with Python standard library (default for single-node deployments).
  - **PostgreSQL:** Version 14, 15, or 16 (recommended for multi-worker production concurrency).
- **Web Server:** Nginx 1.20+ (for reverse proxy and static asset delivery).

---

## 3. Environment Configuration & Variables

Configuration is loaded through environment variables or a `.env` file via `pydantic-settings`.

### Backend Configuration Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `ENVIRONMENT` | string | `development` | Runtime mode: `development`, `production`, or `testing`. |
| `PROJECT_NAME` | string | `farmer-decision-system` | Application name used in logging and OpenAPI specs. |
| `API_V1_STR` | string | `/api` | Root routing prefix for all API endpoints. |
| `HOST` | string | `127.0.0.1` | Local network binding address for Uvicorn. |
| `PORT` | integer | `8000` | Port for the backend API process. |
| `LOG_LEVEL` | string | `INFO` | Logging threshold: `DEBUG`, `INFO`, `WARNING`, `ERROR`. |
| `DATABASE_URL` | string | `sqlite:///data/farmer_decision.db` | SQLAlchemy connection string. |
| `BACKEND_CORS_ORIGINS` | list / string | `["http://localhost:5173", ...]` | Allowed HTTP origins for CORS. In production, explicit origins are enforced. |
| `OPEN_METEO_BASE_URL` | string | `https://api.open-meteo.com/v1` | Open-Meteo REST service endpoint. |
| `OPEN_METEO_TIMEOUT_SECONDS`| float | `10.0` | Network request timeout for weather queries. |
| `OGD_MANDI_API_URL` | string | `https://api.data.gov.in/...` | Official Government of India Mandi API resource URL. |
| `OGD_API_KEY` | string | `None` | Official API key for `data.gov.in`. Never log this value. |
| `OGD_TIMEOUT_SECONDS` | float | `10.0` | Network request timeout for mandi price queries. |

### Frontend Configuration Variables

| Variable | Type | Default | Description |
|---|---|---|---|
| `VITE_API_BASE_URL` | string | `http://127.0.0.1:8000` | Base URL of the backend API used during client network requests. |

---

## 4. Database Setup & Management

### SQLite (Default / Lightweight Single-Node)
- The SQLite database file resides at `data/farmer_decision.db`.
- The backend automatically creates the `data/` directory and creates all tables via `init_db()` upon startup.
- Foreign keys are enforced via an explicit SQLite connection listener (`PRAGMA foreign_keys=ON`).
- Concurrency setting: `connect_args={"check_same_thread": False}`.

### PostgreSQL (Production Scalability)
For multi-process or high-concurrency production deployments:
1. Create a dedicated PostgreSQL database and role:
   ```sql
   CREATE USER farmer_app WITH ENCRYPTED PASSWORD 'StrongProductionPasswordHere';
   CREATE DATABASE farmer_decision_db OWNER farmer_app;
   GRANT ALL PRIVILEGES ON DATABASE farmer_decision_db TO farmer_app;
   ```
2. Set the connection string in `.env`:
   ```bash
   DATABASE_URL="postgresql://farmer_app:StrongProductionPasswordHere@localhost:5432/farmer_decision_db"
   ```
3. The application uses `pool_pre_ping=True` to detect dropped connections and re-establish sessions automatically.

---

## 5. Backend Deployment

### Running with Uvicorn (Direct / Development)
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
```

### Running with Systemd (Linux Service)
Create `/etc/systemd/system/farmer-backend.service`:
```ini
[Unit]
Description=Farmer Decision Support System API
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/farmer-decision-system/backend
EnvironmentFile=/var/www/farmer-decision-system/.env
ExecStart=/var/www/farmer-decision-system/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 4
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
```
Enable and start the service:
```bash
sudo systemctl daemon-reload
sudo systemctl enable farmer-backend
sudo systemctl start farmer-backend
sudo systemctl status farmer-backend
```

---

## 6. Frontend Deployment

### Production Build
```bash
cd frontend
# 1. Install dependencies
npm ci

# 2. Build production bundle into frontend/dist/
npm run build
```

The output bundle will be located in `frontend/dist/` containing `index.html` and static asset chunks (`.js`, `.css`).

---

## 7. Reverse Proxy Configuration (Nginx & SSL)

Create `/etc/nginx/sites-available/farmer-decision.conf`:
```nginx
server {
    listen 80;
    server_name farm.example.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name farm.example.com;

    ssl_certificate /etc/letsencrypt/live/farm.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/farm.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Gzip Compression
    gzip on;
    gzip_types text/plain text/css application/json application/javascript text/xml application/xml;

    # Static Frontend SPA
    root /var/www/farmer-decision-system/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    # API Reverse Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 15s;
        proxy_read_timeout 30s;
    }
}
```
Activate configuration:
```bash
sudo ln -s /etc/nginx/sites-available/farmer-decision.conf /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 8. Security Best Practices

1. **Secrets & Keys:**
   - Never store API keys or database passwords in source code.
   - Use environment variables or secret vaults (e.g., AWS Secrets Manager, HashiCorp Vault).
   - `.env` files are ignored by git in `.gitignore`.
2. **CORS Hardening:**
   - In production (`ENVIRONMENT=production`), wildcard `*` origins are automatically stripped when credentials are used.
   - Specify only trusted browser origins in `BACKEND_CORS_ORIGINS`.
3. **Information Disclosure Prevention:**
   - A global exception handler intercepts unhandled exceptions and returns a clean HTTP 500 response (`{"detail": "Internal server error"}`) with zero stack trace leakage.
   - Entity lookups return standardized 404 responses without internal path data.
4. **Input Validation:**
   - All client inputs are validated via Pydantic schemas before business logic execution.

---

## 9. Health Checks & Monitoring

The system exposes two standard HTTP probes for container orchestrators (Kubernetes / Docker) and uptime monitors:

### 1. Liveness Probe: `GET /api/health`
- **Purpose:** Verifies that the FastAPI process is alive and responsive.
- **Behavior:** Returns `200 OK` instantly without querying the database or external APIs.
- **Example Response:**
  ```json
  {
    "status": "ok",
    "service": "farmer-decision-system"
  }
  ```

### 2. Readiness Probe: `GET /api/ready`
- **Purpose:** Verifies that the service has active, functional connectivity to the primary database.
- **Behavior:** Executes a lightweight `SELECT 1` query.
  - If database is connected: returns `200 OK`.
  - If database is unreachable: returns `503 Service Unavailable`.
  - **Important:** External API outages (Open-Meteo or data.gov.in) do **NOT** fail the readiness check, ensuring system availability.
- **Example Response:**
  ```json
  {
    "status": "ready",
    "database": "connected",
    "environment": "production"
  }
  ```

### Structured Logging
Logs are printed in standardized format:
```text
2026-10-03 21:50:32 | INFO    | farmer_decision_system | Starting farmer-decision-system in production mode
```
Sensitive parameters (API keys, passwords) are never logged.

---

## 10. Data Backup & Recovery

### SQLite Backup
Run a consistent hot backup using the SQLite backup API or command line:
```bash
# Automated daily cron backup
sqlite3 /var/www/farmer-decision-system/data/farmer_decision.db ".backup '/var/backups/farmer_db_$(date +%Y%m%d_%H%M%S).db'"
```

### PostgreSQL Backup
```bash
pg_dump -U farmer_app -h localhost -d farmer_decision_db -F c -b -v -f "/var/backups/farmer_pg_$(date +%Y%m%d_%H%M%S).dump"
```

### Recovery Procedure
1. Stop backend services: `sudo systemctl stop farmer-backend`
2. Restore database file or dump:
   - For SQLite: `cp /var/backups/backup.db /var/www/farmer-decision-system/data/farmer_decision.db`
   - For PostgreSQL: `pg_restore -U farmer_app -d farmer_decision_db /var/backups/backup.dump`
3. Restart backend service: `sudo systemctl start farmer-backend`
4. Confirm health: `curl http://127.0.0.1:8000/api/ready`

---

## 11. Troubleshooting & FAQ

### Issue: `503 Service Unavailable` on `/api/ready`
- **Cause:** Backend cannot connect to SQLite file (file permissions) or PostgreSQL server is down.
- **Resolution:** Check file read/write permissions on `data/farmer_decision.db` or verify `sudo systemctl status postgresql`.

### Issue: Open-Meteo weather fetch timeout
- **Cause:** Temporary network latency or restricted outbound firewall.
- **Resolution:** Verify outbound internet access to `api.open-meteo.com` on port 443. Adjust `OPEN_METEO_TIMEOUT_SECONDS` if needed.

### Issue: Mandi data sync fails with `OGD API key required`
- **Cause:** `OGD_API_KEY` is not set in `.env`.
- **Resolution:** Register on `data.gov.in`, generate an API key, and set `OGD_API_KEY="your_key"` in `.env`.

### Issue: Frontend displays "Unable to connect to backend server"
- **Cause:** `VITE_API_BASE_URL` points to an incorrect URL or CORS rejected the request.
- **Resolution:** Verify that `VITE_API_BASE_URL` in `frontend/.env` matches the backend host, and `BACKEND_CORS_ORIGINS` includes the frontend URL.

---

## 12. Operational Runbook & Maintenance

### Daily Checks
- Confirm `/api/health` and `/api/ready` return 200.
- Check disk space on host volume (`df -h`).

### Applying Application Updates
```bash
# 1. Pull latest code
git pull origin main

# 2. Update backend dependencies
cd backend
source venv/bin/activate
pip install -r requirements.txt

# 3. Build frontend
cd ../frontend
npm ci
npm run build

# 4. Restart backend service
sudo systemctl restart farmer-backend
```

### Log Rotation
Configure `/etc/logrotate.d/farmer-decision` to prevent logs from consuming disk space:
```text
/var/log/farmer-decision/*.log {
    daily
    missingok
    rotate 14
    compress
    delaycompress
    notifempty
    create 0640 www-data www-data
}
```
