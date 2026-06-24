# iGosa — WhatsApp AI Platform for Estate Agents

> Your phone now answers buyers 24/7, follows up automatically, posts to Facebook, collects documents, and tracks deals — all through WhatsApp.

## Quick Start

```bash
# 1. Clone & setup
git clone <repo-url> igosa
cd igosa
bash scripts/dev_setup.sh

# 2. Edit .env with your API keys
#    - OPENAI_API_KEY (required)
#    - EVOLUTION_API_URL (your Evolution API instance)
#    - EVOLUTION_API_KEY (your Evolution API key)

# 3. Update the demo agent's WhatsApp number
#    Edit scripts/init_db.py and replace 27820000000 with your number

# 4. Start
uvicorn app.main:app --reload --port 8000
```

## Architecture

```
WhatsApp Message → Evolution API → Webhook → Intent Classifier (LLM)
                                                    ↓
                                           Smart Responder (LLM)
                                                    ↓
WhatsApp Response ← Evolution API ← ─ ─ ─ ─ ─ ─ ─ ┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API Server | FastAPI (async Python) |
| AI / LLM | OpenAI GPT-4o-mini |
| WhatsApp | Evolution API (Baileys) |
| Database | SQLite (→ PostgreSQL in prod) |
| Deployment | Render free tier |

## Features (Phased)

### Phase 1 — Foundation (current)
- [x] WhatsApp webhook receiver
- [x] Intent classification (14 intents)
- [x] Entity extraction
- [x] Smart responder with SA context
- [x] Agent & lead management
- [x] Basic listing search

### Phase 2 — Core Intelligence
- [ ] FollowUpBot — automated follow-up sequences
- [ ] DealTracker — pipeline management
- [ ] Voice note transcription (Whisper)
- [ ] Vector search for listings (pgvector/Qdrant)
- [ ] Multi-language code-switching enhancement

### Phase 3 — Revenue Engines
- [ ] SocialPoster — Facebook auto-posting
- [ ] BondAssist — affordability + FLISP
- [ ] DocuCollect — document management + OTP generation
- [ ] ValuationAI — comparable sales engine

### Phase 4 — Scale Features
- [ ] RentalManager — full portfolio
- [ ] MarketWatch — competitor intelligence
- [ ] MultiAgent — cross-agent listing pool
- [ ] Web dashboard

## Project Structure

```
igosa/
├── app/
│   ├── main.py              # FastAPI entry point
│   ├── config.py            # Settings from env
│   ├── ai/                  # AI modules
│   │   ├── intent.py        # Intent classifier
│   │   ├── extractor.py     # Entity extractor
│   │   └── responder.py     # Smart response generator
│   ├── routers/
│   │   └── webhook.py       # Evolution API webhook handler
│   └── services/
│       ├── evolution.py     # Evolution API client
│       └── database.py      # Database models & session
├── scripts/
│   ├── init_db.py           # Database initialization
│   └── dev_setup.sh         # Dev environment setup
├── tests/
├── requirements.txt
├── render.yaml              # Render deployment config
└── .env.example
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Service info |
| `/webhook/evolution` | POST | Evolution API webhook |
| `/webhook/evolution` | GET | Webhook verification |
| `/webhook/health` | GET | Health check |
| `/docs` | GET | Swagger docs (dev only) |

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `EVOLUTION_API_URL` | Yes | Evolution API base URL |
| `EVOLUTION_API_KEY` | Yes | Evolution API key |
| `WEBHOOK_SECRET` | Yes | Webhook signature secret |
| `DATABASE_URL` | No | Database URL (defaults to SQLite) |

## License

Private — iGosa Platform
