# Deployment Guide — Smart Disaster Command Center

This guide covers full production deployment of the backend (Render) and frontend (Vercel).

---

## Overview

| Component | Platform | URL Pattern |
|-----------|----------|-------------|
| Backend API | Render (free web service) | `https://your-app.onrender.com` |
| Frontend | Vercel (static hosting) | `https://your-app.vercel.app` |

---

## Step 1 — Push to GitHub

Before deploying, make sure the repo is clean and pushed.

```bash
git init
git add .
git commit -m "Initial production-ready release"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/disaster-command-center.git
git push -u origin main
```

> **Important:** `.env` must **not** be pushed. It is already in `.gitignore`.  
> Push `.env.example` instead — this is safe.

---

## Step 2 — Deploy Backend on Render

### 2.1 Create Render Service

1. Go to [https://render.com](https://render.com) → **New +** → **Web Service**
2. Connect your GitHub repository
3. Render will auto-detect `render.yaml` — click **Apply**

### 2.2 Manual Configuration (if render.yaml not detected)

| Field | Value |
|-------|-------|
| **Runtime** | Python 3 |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `uvicorn backend.main:app --host 0.0.0.0 --port $PORT` |
| **Health Check Path** | `/health` |
| **Plan** | Free |

### 2.3 Set Environment Variables in Render Dashboard

Go to **Environment** → Add each variable:

| Variable | Value | Required |
|----------|-------|----------|
| `GEMINI_API_KEY1` | Your Gemini API key 1 | Yes |
| `GEMINI_API_KEY2` | Your Gemini API key 2 | Yes |
| `GEMINI_API_KEY3` | Your Gemini API key 3 | Recommended |
| `GEMINI_API_KEY4` | Your Gemini API key 4 | Optional |
| `GEMINI_API_KEY5` | Your Gemini API key 5 | Optional |
| `HF_TOKEN` | HuggingFace token (for Qwen fallback) | Recommended |
| `FRONTEND_URL` | `https://your-app.vercel.app` | Yes |
| `PYTHONIOENCODING` | `utf-8` | Recommended |
| `PYTHONUNBUFFERED` | `1` | Recommended |

> **Note on FRONTEND_URL:** This must match your Vercel deployment URL exactly.  
> Example: `https://disaster-command-center.vercel.app`

### 2.4 Health Checks

Render automatically pings `/health` every 30 seconds.

Test manually after deployment:
```bash
curl https://your-app.onrender.com/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "disaster-command-center-backend",
  "version": "1.0.0"
}
```

### 2.5 Copy the Backend URL

Once deployed, copy the full URL (e.g. `https://disaster-command-center.onrender.com`).  
You will need it for Step 3.

---

## Step 3 — Deploy Frontend on Vercel

### 3.1 Update vercel.json

Open `vercel.json` and replace the placeholder:

```json
"destination": "https://YOUR_BACKEND_URL.onrender.com/api/:path*"
```

With your actual Render URL:

```json
"destination": "https://disaster-command-center.onrender.com/api/:path*"
```

Commit and push this change:
```bash
git add vercel.json
git commit -m "Set production backend URL in vercel.json"
git push
```

### 3.2 Deploy to Vercel

**Option A — Vercel Dashboard (recommended)**
1. Go to [https://vercel.com](https://vercel.com) → **New Project**
2. Import your GitHub repository
3. Leave **Root Directory** as `./`
4. Click **Deploy**

**Option B — Vercel CLI**
```bash
npm i -g vercel
vercel
```

### 3.3 Frontend Environment Variables

The frontend (`frontend/js/app.js`) auto-detects the API base URL:

```js
const API_BASE = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
    ? "http://localhost:8000/api"
    : "/api";
```

- **Local**: points to `http://localhost:8000/api` automatically
- **Production**: points to `/api` — Vercel rewrites this to your Render backend via `vercel.json`

No environment variable injection is needed in the frontend.

---

## Step 4 — UptimeRobot Monitoring (Optional)

UptimeRobot will ping `/health` every 5 minutes to keep your Render free-tier service warm and alert you on downtime.

1. Go to [https://uptimerobot.com](https://uptimerobot.com)
2. **New Monitor** → **HTTP(s)**
3. Set:
   - **Friendly Name**: `Disaster Command Center API`
   - **URL**: `https://your-app.onrender.com/health`
   - **Monitoring Interval**: 5 minutes
4. Enable email/SMS alerts

> **Why this matters:** Render free-tier services spin down after 15 minutes of inactivity.  
> UptimeRobot pings keep the service warm and catch failures early.

---

## Step 5 — Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variables
cp .env.example .env
# Edit .env — fill in GEMINI_API_KEY1..5 and HF_TOKEN

# 3. Start backend
python backend/main.py

# 4. Open in browser
# http://localhost:8000
```

**Windows PowerShell — kill and restart backend:**
```powershell
Get-CimInstance Win32_Process -Filter "CommandLine LIKE '%backend/main.py%'" | Invoke-CimMethod -MethodName Terminate; python backend/main.py
```

---

## Troubleshooting

### CORS Error in Browser (403/Network Error)

**Cause:** `FRONTEND_URL` is not set in Render environment variables.  
**Fix:** In Render Dashboard → Environment → Add:
```
FRONTEND_URL = https://your-app.vercel.app
```

### AI Assistant Returns "Rule Engine" Response

**Cause:** All Gemini keys are quota-exhausted AND Qwen API is unavailable.  
**Fix:**
- Check Gemini key quotas at [https://ai.dev/rate-limit](https://ai.dev/rate-limit)
- Verify `HF_TOKEN` is set correctly in Render environment variables
- Rule Engine responses are deterministic and data-accurate — they are safe

### Render Service Sleeping (504 Timeout on First Request)

**Cause:** Free-tier services sleep after 15 min of inactivity.  
**Fix:** Set up UptimeRobot as described in Step 4.

### `uvicorn` Not Found on Render

**Cause:** `uvicorn` not in requirements.  
**Fix:** Verify `requirements.txt` contains:
```
uvicorn>=0.24.0
```

### Frontend Shows "Failed to Load Districts"

**Cause:** Vercel → Render API proxy not configured.  
**Fix:** Verify `vercel.json` contains your actual Render URL (not the `YOUR_BACKEND_URL` placeholder).

---

## Environment Variables Reference

| Variable | Used By | Required | Description |
|----------|---------|----------|-------------|
| `GEMINI_API_KEY1` | Backend | Yes | Gemini 2.5 Flash key 1 (round-robin Tier 1) |
| `GEMINI_API_KEY2` | Backend | Yes | Gemini 2.5 Flash key 2 |
| `GEMINI_API_KEY3` | Backend | Recommended | Gemini 2.5 Flash key 3 (quota resilience) |
| `GEMINI_API_KEY4` | Backend | Optional | Gemini 2.5 Flash key 4 |
| `GEMINI_API_KEY5` | Backend | Optional | Gemini 2.5 Flash key 5 |
| `HF_TOKEN` | Backend | Recommended | HuggingFace token — Qwen 2.5 7B fallback (Tier 2) |
| `FRONTEND_URL` | Backend | Yes (prod) | Vercel deployment URL for CORS (e.g. `https://app.vercel.app`) |
| `PYTHONIOENCODING` | System | No | Forces UTF-8 log encoding |
| `PYTHONUNBUFFERED` | System | No | Disables log buffering (live logs on Render) |
