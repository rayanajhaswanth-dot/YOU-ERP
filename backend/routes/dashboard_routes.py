from fastapi import APIRouter
from pydantic import BaseModel
import os

from database import get_supabase

router = APIRouter()


class DraftRequest(BaseModel):
    raw_topic: str


@router.get("/grievances")
async def get_critical_grievances():
    """
    Fetch CRITICAL or HIGH priority issues for the 'Crisis Feed'.
    Filters by Priority AND Politician ID to ensure data privacy.
    """
    try:
        supabase = get_supabase()
        pid = os.getenv("POLITICIAN_ID", "6e56793a-558b-4834-ab0d-36387159653a")
        
        response = supabase.table("grievances")\
            .select("id, issue_type, village, description, priority_level, created_at")\
            .eq("politician_id", pid)\
            .or_("priority_level.eq.CRITICAL,priority_level.eq.HIGH")\
            .order("created_at", desc=True)\
            .limit(5)\
            .execute()
        
        return response.data
    except Exception as e:
        print(f"Error fetching grievances: {e}")
        return []


@router.get("/stats")
async def get_dashboard_stats():
    """
    Get quick stats for the dashboard header.
    """
    try:
        supabase = get_supabase()
        pid = os.getenv("POLITICIAN_ID", "6e56793a-558b-4834-ab0d-36387159653a")
        
        # Get grievance counts by status
        grievances = supabase.table("grievances")\
            .select("status, priority_level")\
            .eq("politician_id", pid)\
            .execute()
        
        data = grievances.data or []
        
        pending = sum(1 for g in data if g.get('status', '').upper() == 'PENDING')
        critical = sum(1 for g in data if g.get('priority_level', '').upper() == 'CRITICAL')
        resolved = sum(1 for g in data if g.get('status', '').upper() == 'RESOLVED')
        
        return {
            "pending_grievances": pending,
            "critical_alerts": critical,
            "resolved_today": resolved,
            "total": len(data)
        }
    except Exception as e:
        print(f"Error fetching stats: {e}")
        return {"pending_grievances": 0, "critical_alerts": 0, "resolved_today": 0, "total": 0}


@router.post("/draft")
async def draft_post(req: DraftRequest):
    """
    Simulated AI Drafting for instant UI feedback.
    Returns pre-formatted drafts for different platforms.
    """
    topic = req.raw_topic
    
    return {
        "twitter": f"🚨 UPDATE: {topic}. We are working tirelessly for you! #ConstituencyFirst",
        "whatsapp": f"🙏 Namaste. Important Update regarding {topic}. Your Sevak, [Leader Name].",
        "facebook": f"OFFICIAL STATEMENT: {topic}. Our commitment to development remains strong."
    }
