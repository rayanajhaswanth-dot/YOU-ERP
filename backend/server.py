from fastapi import FastAPI, APIRouter
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path

from routes import auth_routes, grievance_routes, posts_routes, analytics_routes, ai_routes, whatsapp_routes

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

app = FastAPI(title="YOU - Governance ERP", version="1.0.0")

api_router = APIRouter(prefix="/api")

api_router.include_router(auth_routes.router, prefix="/auth", tags=["auth"])
api_router.include_router(grievance_routes.router, prefix="/grievances", tags=["grievances"])
api_router.include_router(posts_routes.router, prefix="/posts", tags=["posts"])
api_router.include_router(analytics_routes.router, prefix="/analytics", tags=["analytics"])
api_router.include_router(ai_routes.router, prefix="/ai", tags=["ai"])
api_router.include_router(whatsapp_routes.router, prefix="/whatsapp", tags=["whatsapp"])

@api_router.get("/")
async def root():
    return {"message": "YOU - Governance ERP API", "version": "1.0.0"}

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)