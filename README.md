# EASTEND — Autonomous Social Media Growth Agent

An end-to-end system that manages Instagram and TikTok accounts for **EASTEND Salon**, East London. It publishes 3 optimised posts per day per platform, learns from performance data, and continuously refines strategy.

---

## Architecture

```
┌─────────────────────────────────┐
│         React Dashboard          │  ← Vite + Tailwind (port 5173)
└────────────────┬────────────────┘
                 │ /api/*
┌────────────────▼────────────────┐
│         FastAPI Backend          │  ← Python 3.11 (port 8000)
│  ┌──────────┐  ┌─────────────┐  │
│  │Scheduler │  │  AI Engine  │  │  ← APScheduler + Claude API
│  └──────────┘  └─────────────┘  │
│  ┌──────────┐  ┌─────────────┐  │
│  │Instagram │  │   TikTok    │  │  ← Graph API + Content Posting API
│  └──────────┘  └─────────────┘  │
│  ┌──────────────────────────┐   │
│  │      SQLite Database     │   │
│  └──────────────────────────┘   │
└─────────────────────────────────┘
```

---

## Quick Start

### 1. Clone & configure

```bash
cp .env.example .env
# Edit .env — add your API keys
```

### 2. Run with Docker Compose

```bash
docker-compose up --build
```

Dashboard → http://localhost:3000

### 3. Or run locally

**Backend:**
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend:**
```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

---

## Configuration

All settings live in `.env` (copy from `.env.example`):

| Key | Description |
|-----|-------------|
| `ANTHROPIC_API_KEY` | Claude AI — powers captions, hooks, reports |
| `INSTAGRAM_ACCESS_TOKEN` | Long-lived Instagram Business token |
| `INSTAGRAM_BUSINESS_ACCOUNT_ID` | Your IG Business Account ID |
| `TIKTOK_ACCESS_TOKEN` | TikTok creator access token |
| `DEMO_MODE=true` | No real API calls — use this until credentials are ready |
| `APPROVAL_REQUIRED=true` | All posts require your approval (set false for full autonomy) |

---

## Getting API Credentials

### Instagram Graph API
1. Go to developers.facebook.com
2. Create an app → Add Instagram product
3. Get your Business Account ID and generate a long-lived access token
4. Paste into `.env`

### TikTok Content Posting API
1. Go to developers.tiktok.com
2. Create an app → apply for Content Posting API access
3. Generate access token via OAuth
4. Paste into `.env`

### Anthropic (Claude AI)
1. Go to console.anthropic.com
2. Create an API key
3. Paste into `.env`

---

## Workflow

```
Upload video/image
        ↓
AI analyses asset (brand fit, pillar, hook ideas)
        ↓
AI generates caption, hook, hashtags, audio suggestion
        ↓
Post enters Approval Queue
        ↓
Owner approves + sets schedule time (or auto-schedule)
        ↓
Scheduler publishes at optimal time
        ↓
Metrics collected at 1h, 6h, 24h, 72h, 7d
        ↓
Learning loop updates pattern library
        ↓
AI suggestions improve for next batch
        ↓
Weekly strategy report generated (Mondays 09:00)
```

---

## Dashboard Pages

| Page | Description |
|------|-------------|
| **Dashboard** | Overview stats, today's posts, pending approvals |
| **Content Feed** | All posts filterable by platform/status/pillar |
| **Approval Queue** | Review AI-generated posts before they publish |
| **Analytics** | Views, engagement, platform comparisons |
| **Trend Tracker** | Trending sounds and hashtags, viral benchmarks |
| **Suggestions** | 5 AI-recommended next posts with reasoning |
| **Reports** | Weekly strategy reports with wins/losses |
| **Upload** | Upload content and trigger AI generation |

---

## Legal Notice

All colour service posts automatically include the required patch test notice:
"Patch test required 48hrs before any colour service. DM us to arrange."

---

## Brand Bible

See brand_bible.md for EASTEND's full brand guidelines, content rules, and strategy framework.
