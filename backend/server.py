from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
import subprocess
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# APScheduler for Background Tasks
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from services.social_listener import fetch_and_analyze_social_feed

# TextBlob Corpora Download (for Sentiment Engine)
try:
    from textblob import TextBlob
    # Simple test to verify model availability
    TextBlob("test").sentiment
except Exception:
    print("Installing TextBlob Corpora for Sentiment Engine...")
    try:
        subprocess.check_call([sys.executable, "-m", "textblob.download_corpora"])
    except Exception as e:
        print(f"Warning: Could not auto-download corpora. Sentiment analysis might vary. Error: {e}")

from routes import auth_routes, grievance_routes, posts_routes, analytics_routes, ai_routes, whatsapp_routes, verification_routes, social_routes, dashboard_routes, tickets_routes, broadcast_routes

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Setup Scheduler
scheduler = AsyncIOScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- STARTUP ---
    print("🚀 System Starting... Initializing Social Listener.")
    
    # Schedule the Social Listener to run every 5 minutes
    scheduler.add_job(fetch_and_analyze_social_feed, 'interval', minutes=5)
    scheduler.start()
    
    # Run once immediately on startup to populate initial data
    try:
        await fetch_and_analyze_social_feed()
    except Exception as e:
        print(f"⚠️ Initial Social Listener run failed: {e}")
    
    yield
    # --- SHUTDOWN ---
    print("🛑 System Shutting Down...")
    scheduler.shutdown()

app = FastAPI(title="YOU - Governance ERP", version="1.0.0", lifespan=lifespan)

# CORS middleware must be added BEFORE including routers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
api_router.include_router(grievance_routes.router, prefix="/grievances", tags=["grievances"])
api_router.include_router(posts_routes.router, prefix="/posts", tags=["posts"])
api_router.include_router(analytics_routes.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(ai_routes.router, prefix="/ai", tags=["ai"])
api_router.include_router(whatsapp_routes.router, prefix="/whatsapp", tags=["whatsapp"])
api_router.include_router(verification_routes.router, prefix="/verification", tags=["verification"])
api_router.include_router(social_routes.router, prefix="/social", tags=["Social"])
api_router.include_router(dashboard_routes.router, prefix="/dashboard", tags=["Dashboard"])
api_router.include_router(tickets_routes.router, prefix="/tickets", tags=["Tickets"])
api_router.include_router(broadcast_routes.router, prefix="/broadcast", tags=["Broadcast"])

@api_router.get("/")
async def root():
    return {"message": "YOU - Governance ERP API", "version": "1.0.0"}

app.include_router(api_router)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)