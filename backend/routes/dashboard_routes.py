from fastapi import APIRouter
from pydantic import BaseModel
import os

from database import get_supabase

router = APIRouter()


class DraftRequest(BaseModel):
    topic: str = None
    raw_topic: str = None
    tone: str = "professional"


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
    AI Drafting for Broadcast Center.
    Returns pre-formatted drafts for different platforms based on topic and tone.
    """
    # Support both 'topic' and 'raw_topic' field names
    topic = req.topic or req.raw_topic or "Update"
    tone = req.tone
    
    # Tone-based variations
    if tone == "urgent":
        twitter = f"🚨 URGENT: {topic}. Immediate action being taken! #ConstituencyFirst #ActionNow"
        whatsapp = f"⚠️ URGENT UPDATE\n\n{topic}\n\nOur team is on it. Stay informed.\n\n- Your Sevak"
        facebook = f"🔴 URGENT NOTICE\n\n{topic}\n\nWe are taking immediate action. Your safety and well-being are our top priority."
    elif tone == "empathetic":
        twitter = f"We hear you. {topic}. Together, we will overcome. 🙏 #WeStandWithYou"
        whatsapp = f"🙏 Namaste,\n\nWe understand your concerns.\n\n{topic}\n\nWe are here for you.\n\n- Your Sevak"
        facebook = f"Dear Citizens,\n\nYour concerns matter to us deeply.\n\n{topic}\n\nWe are committed to serving you with compassion and dedication."
    elif tone == "political":
        twitter = f"✊ {topic}. This is the change we promised! #Development #Progress #ConstituencyFirst"
        whatsapp = f"✊ Jai Hind!\n\n{topic}\n\nThis is the development we promised. More to come!\n\n- Your Leader"
        facebook = f"DEVELOPMENT UPDATE\n\n{topic}\n\nWhen we made promises, we meant them. This is just the beginning of the transformation we envisioned for our constituency."
    else:  # professional (default)
        twitter = f"📢 UPDATE: {topic}. We remain committed to progress. #ConstituencyFirst #GoodGovernance"
        whatsapp = f"🙏 Namaste,\n\nImportant Update:\n\n{topic}\n\nThank you for your continued support.\n\n- Your Sevak"
        facebook = f"OFFICIAL UPDATE\n\n{topic}\n\nOur commitment to development and good governance remains unwavering. Thank you for your trust."
    
    return {
        "twitter": twitter,
        "whatsapp": whatsapp,
        "facebook": facebook
    }
