"""
iGosa — Unified WhatsApp AI Platform for Estate Agents
========================================================
FastAPI application v0.2 — All modules integrated.

Start: uvicorn app.main:app --reload --port 8000
"""
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.services.database import init_db
from app.services.evolution import evolution
from app.routers import webhook, api

# ── Logging ───────────────────────────────────────────
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ── Background Task Scheduler ────────────────────────
# Lightweight scheduler for processing follow-ups and reminders
# In production, use Celery Beat or external cron hitting /api/tasks/process
scheduler_running = False


async def background_task_loop():
    """Process pending tasks every 60 seconds (dev mode only)."""
    import asyncio
    from app.services.database import AsyncSessionLocal
    from app.services.followup import follow_up_manager
    from app.services.rentals import rental_manager

    global scheduler_running
    scheduler_running = True
    logger.info("⏰ Background task scheduler started")

    while True:
        await asyncio.sleep(60)  # Check every minute
        try:
            async with AsyncSessionLocal() as db:
                # Process follow-ups
                sent = await follow_up_manager.process_due_tasks(db)
                if sent > 0:
                    logger.info(f"📤 Processed {sent} follow-up tasks")

                # Check for end-of-month rental reset
                from datetime import datetime
                if datetime.utcnow().day == 1 and datetime.utcnow().hour == 0:
                    await rental_manager.process_monthly_tasks(db)
        except Exception as e:
            logger.error(f"Background task error: {e}", exc_info=True)


# ── Application Lifecycle ─────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    # ── STARTUP ────────────────────────────────────
    logger.info("🚀 iGosa v0.2 starting up...")
    logger.info(f"📡 Environment: {settings.environment}")
    logger.info(f"🤖 AI Provider: {settings.ai_provider}")
    logger.info(f"💬 Evolution API: {settings.evolution_api_url}")

    # Initialize database
    try:
        await init_db()
        logger.info("🗄️  Database initialized")
    except Exception as e:
        logger.error(f"❌ Database init failed: {e}")
        raise

    # Check Evolution API + webhook
    try:
        status = await evolution.get_instance_status()
        logger.info(f'📱 Evolution: {status}')
    except Exception as e:
        logger.warning(f'⚠️  Evolution API not reachable: {e}')
        logger.warning('   WhatsApp will not work until Evolution is connected.')

    # Start background task scheduler
    import asyncio
    scheduler_task = asyncio.create_task(background_task_loop())

    logger.info("✅ iGosa is ready!")

    yield  # Application runs here

    # ── SHUTDOWN ───────────────────────────────────
    scheduler_task.cancel()
    logger.info("👋 iGosa shutting down...")


# ── App Instance ──────────────────────────────────────

app = FastAPI(
    title="iGosa — WhatsApp AI for Estate Agents",
    description="Unified WhatsApp-first AI platform for South African estate agents.",
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url=None,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.environment == "development" else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files (dashboard)
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

# Register routers
app.include_router(webhook.router)
app.include_router(api.router)


# ── Root ──────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "name": "iGosa",
        "version": "0.2.0",
        "description": "WhatsApp AI Platform for SA Estate Agents",
        "status": "running",
        "endpoints": {
            "webhook": "/webhook/evolution",
            "api": "/api",
            "dashboard": "/static/dashboard.html",
            "health": "/webhook/health",
            "docs": "/docs" if settings.environment == "development" else None,
        },
    }


@app.get("/dashboard")
async def dashboard_redirect():
    """Redirect to the dashboard."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/dashboard.html")
