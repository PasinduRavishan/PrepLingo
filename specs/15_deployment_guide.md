# SPEC 15 — GCP VPS Deployment Guide

Status: Active reference
Date: 2026-03-17
Target: Single GCP Compute Engine VM running all services via Docker Compose

---

## Architecture

```
Internet
    │
    ▼ :80 (or :443 with HTTPS)
┌─────────────────────────────────────────────────┐
│  GCP Compute Engine VM  (e2-medium, Ubuntu 22)  │
│                                                 │
│  ┌──────────────────────────────────────────┐   │
│  │  nginx:1.25 (container, port 80)         │   │
│  │  /api/*  → backend:8000 (internal)       │   │
│  │  /*      → frontend:8501 (internal)      │   │
│  └──────────────────────────────────────────┘   │
│            │                    │               │
│  ┌─────────▼──────┐  ┌─────────▼──────────┐    │
│  │ backend:8000   │  │  frontend:8501     │    │
│  │ FastAPI+Groq   │  │  Streamlit         │    │
│  │ ChromaDB       │  │  calls backend     │    │
│  │ BAAI embedding │  │  via Docker net    │    │
│  └────────────────┘  └────────────────────┘    │
│                                                 │
│  Named Docker Volumes                           │
│  embedding-cache  → /root/.cache/huggingface    │
│  vector-data      → ChromaDB index on disk      │
│  db-data          → SQLite database             │
└─────────────────────────────────────────────────┘
```

Key: the frontend's Python `requests` calls go **backend → backend container** via the internal Docker network (`http://backend:8000`). The user's browser only talks to nginx on port 80.

---

## File Structure Added for Deployment

```
PrepLingo/
├── docker-compose.yml          ← Orchestrates all 3 containers
├── .env.example                ← Root env template for docker-compose
├── .env                        ← Your secrets (gitignored)
│
├── nginx/
│   └── nginx.conf              ← Nginx routing rules (API + Streamlit WS)
│
├── backend/
│   └── Dockerfile              ← Multi-stage: pre-downloads BAAI model
│
└── frontend_streamlit/
    └── Dockerfile              ← Simple Python image running Streamlit
```

---

## Part 1 — Prepare Locally Before Deploying

### 1.1 Check .gitignore covers secrets

Make sure these are in `.gitignore` at the root:

```gitignore
.env
backend/.env
*.db
vector_store_data/
backend/.venv/
__pycache__/
*.pyc
```

### 1.2 Test docker-compose locally first

```bash
# From project root
cp .env.example .env
# Edit .env — set GROQ_API_KEY

docker-compose up --build
```

Check:
- `http://localhost/health` → `{"status": "ok"}`
- `http://localhost/` → Streamlit UI
- `http://localhost/docs` → FastAPI Swagger

```bash
# Ingest knowledge base (one time, while containers are running)
docker-compose exec backend python scripts/ingest_knowledge.py

# Stop
docker-compose down
```

---

## Part 2 — Create the GCP VM

### 2.1 Open GCP Console

Go to: **Compute Engine → VM Instances → Create Instance**

### 2.2 VM Configuration

| Setting | Value |
|---------|-------|
| Name | `preplingo-vm` |
| Region | `us-central1` (or closest to your users) |
| Zone | `us-central1-a` |
| Machine type | `e2-medium` (2 vCPU, 4 GB RAM) |
| Boot disk OS | **Ubuntu 22.04 LTS** |
| Boot disk size | **30 GB** (SSD) |
| Firewall | ✅ Allow HTTP traffic |
| Firewall | ✅ Allow HTTPS traffic (for later) |

> **Why e2-medium?** The BAAI embedding model needs ~1.5 GB RAM at runtime. FastAPI + Streamlit + nginx add another ~500 MB. 4 GB gives comfortable headroom.

### 2.3 Add a Firewall Rule for SSH (already open by default)

If port 22 is already open you're good. If not:
**VPC Network → Firewall → Create Firewall Rule:**
- Name: `allow-ssh`
- Targets: All instances
- Source: `0.0.0.0/0`
- Protocols: TCP port 22

---

## Part 3 — Set Up the VM

### 3.1 SSH into the VM

From GCP Console click **SSH** next to the VM, or from your terminal:

```bash
gcloud compute ssh preplingo-vm --zone us-central1-a
```

### 3.2 Install Docker

```bash
# Update packages
sudo apt-get update && sudo apt-get upgrade -y

# Install Docker (official script)
curl -fsSL https://get.docker.com | sudo sh

# Add your user to the docker group (no sudo needed for docker commands)
sudo usermod -aG docker $USER

# Apply group change — log out and back in, OR run:
newgrp docker

# Verify
docker --version
docker compose version
```

### 3.3 Install Git

```bash
sudo apt-get install -y git
```

---

## Part 4 — Deploy the Application

### 4.1 Clone the repository

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/PrepLingo.git
cd PrepLingo
```

### 4.2 Create the .env file

```bash
cp .env.example .env
nano .env
```

Set your values:
```env
GROQ_API_KEY=gsk_YOUR_REAL_KEY_HERE
JWT_SECRET_KEY=<run: python3 -c "import secrets; print(secrets.token_hex(32))">
APP_ENV=production
```

Save and exit: `Ctrl+X → Y → Enter`

### 4.3 Build and start all containers

```bash
# First build takes 5-10 minutes (downloads BAAI model ~430 MB into image)
docker compose up --build -d

# Watch startup logs
docker compose logs -f
```

Expected sequence:
1. `backend` builds (downloads BAAI model into image layer)
2. `frontend` builds (quick — just pip install streamlit)
3. `nginx` pulls from Docker Hub
4. `backend` starts, health check passes
5. `frontend` starts (waits for backend healthy)
6. `nginx` starts and begins routing

### 4.4 Ingest the knowledge base (one time)

```bash
docker compose exec backend python scripts/ingest_knowledge.py
```

Expected output:
```
Loading embedding model: BAAI/bge-base-en-v1.5
Scanning knowledge_base/ ...
Embedding N documents → ChromaDB
✅ Knowledge ingestion complete.
```

### 4.5 Verify everything works

```bash
# Get the VM's external IP
curl ifconfig.me

# Or check from GCP Console → VM Instances → External IP
```

Test in browser:
- `http://YOUR_VM_IP/` → PrepLingo Streamlit UI
- `http://YOUR_VM_IP/health` → `{"status": "ok"}`
- `http://YOUR_VM_IP/docs` → FastAPI Swagger

---

## Part 5 — Set Up HTTPS (Recommended)

HTTPS is required for any real users. Two approaches:

### Option A — Point a Domain (Recommended)

**Step 1:** Buy or use a free domain. Free options: Freenom, DuckDNS, no-ip.

**Step 2:** Add a DNS A record pointing your domain to the VM's external IP.
```
A record:  preplingo.yourdomain.com  →  34.X.X.X  (your VM IP)
```

**Step 3:** Update nginx.conf to use your domain:

Open `nginx/nginx.conf` and change:
```nginx
server_name _;
```
to:
```nginx
server_name preplingo.yourdomain.com;
```

**Step 4:** Install Certbot inside the VM (not in Docker):

```bash
# On the VM (not inside a container)
sudo apt-get install -y certbot

# Stop nginx container temporarily to free port 80
docker compose stop nginx

# Get certificate
sudo certbot certonly --standalone -d preplingo.yourdomain.com

# Certs are saved at:
# /etc/letsencrypt/live/preplingo.yourdomain.com/fullchain.pem
# /etc/letsencrypt/live/preplingo.yourdomain.com/privkey.pem
```

**Step 5:** Update `nginx/nginx.conf` for HTTPS:

```nginx
# Redirect HTTP to HTTPS
server {
    listen 80;
    server_name preplingo.yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name preplingo.yourdomain.com;

    ssl_certificate     /etc/nginx/certs/fullchain.pem;
    ssl_certificate_key /etc/nginx/certs/privkey.pem;

    client_max_body_size 20M;

    location /api/ {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 120s;
        proxy_send_timeout 120s;
    }

    location /health { proxy_pass http://backend:8000; }
    location /docs   { proxy_pass http://backend:8000; }
    location /openapi.json { proxy_pass http://backend:8000; }

    location / {
        proxy_pass http://frontend:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }

    location /_stcore/ {
        proxy_pass http://frontend:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400s;
    }
}
```

**Step 6:** Mount certs into nginx container. Update `docker-compose.yml` nginx volumes:

```yaml
volumes:
  - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
  - /etc/letsencrypt/live/preplingo.yourdomain.com/fullchain.pem:/etc/nginx/certs/fullchain.pem:ro
  - /etc/letsencrypt/live/preplingo.yourdomain.com/privkey.pem:/etc/nginx/certs/privkey.pem:ro
```

Uncomment port 443 in docker-compose.yml nginx ports:
```yaml
ports:
  - "80:80"
  - "443:443"
```

**Step 7:** Restart nginx:
```bash
docker compose up -d nginx
```

**Step 8:** Set up auto-renewal (certs expire every 90 days):
```bash
# Add to crontab
sudo crontab -e

# Add this line (runs renewal check twice daily):
0 0,12 * * * certbot renew --quiet && docker compose -f /home/$USER/PrepLingo/docker-compose.yml restart nginx
```

### Option B — No Domain (VM IP Only)

Use HTTP only (port 80). Fine for demos and internal testing. Skip Part 5 entirely.

---

## Part 6 — Day-to-Day Operations

### View logs

```bash
cd ~/PrepLingo

# All containers
docker compose logs -f

# Specific service
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f nginx
```

### Deploy an update

```bash
cd ~/PrepLingo
git pull

# Rebuild only changed services (Docker caches unchanged layers)
docker compose up --build -d

# If you changed knowledge base docs, re-ingest
docker compose exec backend python scripts/ingest_knowledge.py
```

### Restart services

```bash
# Restart all
docker compose restart

# Restart one
docker compose restart backend
docker compose restart frontend
```

### Stop everything

```bash
docker compose down

# Stop AND delete volumes (WARNING: loses ChromaDB + SQLite data)
docker compose down -v
```

### Check container status

```bash
docker compose ps
```

Expected output:
```
NAME                  STATUS          PORTS
preplingo-backend     Up (healthy)    8000/tcp
preplingo-frontend    Up              8501/tcp
preplingo-nginx       Up              0.0.0.0:80->80/tcp
```

### Check disk usage

```bash
df -h                        # VM disk usage
docker system df             # Docker volumes + images
```

---

## Part 7 — Auto-Start on VM Reboot

Docker containers with `restart: unless-stopped` start automatically when Docker starts. Make Docker start on boot:

```bash
sudo systemctl enable docker
```

Verify:
```bash
sudo systemctl status docker
```

---

## Part 8 — GCP Firewall Rules Summary

GCP Compute Engine VMs need firewall rules to allow traffic. These should be configured automatically when you tick "Allow HTTP/HTTPS" during VM creation. If not:

Go to: **VPC Network → Firewall → Create Firewall Rule**

| Rule Name | Direction | Target | Source | Port |
|-----------|-----------|--------|--------|------|
| `allow-http` | Ingress | All | 0.0.0.0/0 | TCP 80 |
| `allow-https` | Ingress | All | 0.0.0.0/0 | TCP 443 |
| `allow-ssh` | Ingress | All | Your IP | TCP 22 |

> ⚠️ Do NOT open port 8000 or 8501 publicly. All traffic goes through nginx on port 80/443.

---

## Part 9 — Environment Variable Reference

All vars read from root `.env` by docker-compose:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GROQ_API_KEY` | **Yes** | — | Groq API key |
| `GROQ_MODEL` | No | `llama-3.3-70b-versatile` | Primary LLM |
| `GROQ_FALLBACK_MODEL` | No | `llama-3.1-8b-instant` | Fallback LLM on 429 |
| `EMBEDDING_MODEL` | No | `BAAI/bge-base-en-v1.5` | Local embedding model |
| `DATABASE_URL` | No | `sqlite:///./preplingo.db` | SQLite for dev/prod |
| `VECTOR_STORE_PATH` | No | `./vector_store_data` | ChromaDB path |
| `JWT_SECRET_KEY` | No | dev value | **Change in production** |
| `APP_ENV` | No | `production` | App environment |

---

## Part 10 — Troubleshooting

### Containers won't start

```bash
docker compose logs backend   # Check for missing env vars or import errors
docker compose logs frontend  # Check for BACKEND_URL issues
```

### Health check failing (backend shows "starting")

The first start downloads nothing (BAAI model is baked into image), but SQLModel needs to create DB tables. Wait 15-20 seconds for `start_period` to pass.

```bash
docker compose ps              # Check STATUS column
docker compose logs backend    # Look for "Application startup complete"
```

### Streamlit shows blank page or connection error

```bash
docker compose logs frontend   # Look for startup errors
docker compose logs nginx      # Look for upstream connection errors
```

Streamlit needs the WebSocket to work. Ensure nginx.conf has the `Upgrade` headers for `location /` and `location /_stcore/`.

### Knowledge base not returning relevant results

Re-run ingestion:
```bash
docker compose exec backend python scripts/ingest_knowledge.py
```

If you want a clean rebuild:
```bash
docker compose exec backend rm -rf vector_store_data/
docker compose exec backend python scripts/ingest_knowledge.py
```

### Disk full

```bash
df -h                          # Check disk usage
docker system prune -f         # Remove stopped containers and dangling images
docker image prune -a          # Remove unused images (careful — triggers rebuild)
```

### GROQ rate limit errors visible in logs

Normal — the fallback (`llama-3.1-8b-instant`) activates automatically. If you see frequent fallback triggers, consider upgrading to a Groq paid plan ($0.01-0.05/1M tokens).

---

## Quick Reference: Deploy From Scratch

```bash
# 1. SSH into VM
gcloud compute ssh preplingo-vm --zone us-central1-a

# 2. Install Docker (first time only)
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER && newgrp docker

# 3. Clone repo (first time only)
git clone https://github.com/YOUR_USERNAME/PrepLingo.git ~/PrepLingo
cd ~/PrepLingo

# 4. Configure secrets (first time only)
cp .env.example .env && nano .env   # Set GROQ_API_KEY

# 5. Start everything
docker compose up --build -d

# 6. Ingest knowledge base (first time only)
docker compose exec backend python scripts/ingest_knowledge.py

# 7. Get your public URL
curl ifconfig.me
# → open http://THAT_IP in browser
```

---

## Quick Reference: Update Deployment

```bash
cd ~/PrepLingo
git pull
docker compose up --build -d
# If knowledge base docs changed:
docker compose exec backend python scripts/ingest_knowledge.py
```
