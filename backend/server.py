from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
import subprocess
import sys
from pathlib import Path

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

from routes import auth_routes, grievance_routes, posts_routes, analytics_routes, ai_routes, whatsapp_routes, verification_routes, social_routes, dashboard_routes

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI(title="YOU - Governance ERP", version="1.0.0")

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

@api_router.get("/")
async def root():
    return {"message": "YOU - Governance ERP API", "version": "1.0.0"}

app.include_router(api_router)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)