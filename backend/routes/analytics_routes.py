from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from database import get_supabase
from auth import get_current_user, TokenData
from datetime import datetime, timezone, timedelta
import uuid

router = APIRouter()

class SentimentData(BaseModel):
    platform: str
    sentiment_score: float
    issue_category: str
    content: str

@router.post("/sentiment")
async def create_sentiment_entry(
    data: SentimentData,
    current_user: TokenData = Depends(get_current_user)
):
    if not current_user.politician_id:
        raise HTTPException(status_code=403, detail="User not associated with a politician")
    
    supabase = get_supabase()
    entry_id = str(uuid.uuid4())
    
    sentiment_data = {
        'id': entry_id,
        'politician_id': current_user.politician_id,
        'platform': data.platform,
        'sentiment_score': data.sentiment_score,
        'issue_category': data.issue_category,
        'content': data.content,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    result = supabase.table('sentiment_analytics').insert(sentiment_data).execute()
    return {"message": "Sentiment entry created successfully", "id": entry_id}

@router.get("/sentiment")
async def get_sentiment_data(
    days: int = 30,
    current_user: TokenData = Depends(get_current_user)
):
    if not current_user.politician_id:
        raise HTTPException(status_code=403, detail="User not associated with a politician")
    
    supabase = get_supabase()
    start_date = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    
    result = supabase.table('sentiment_analytics').select('*').eq('politician_id', current_user.politician_id).gte('created_at', start_date).order('created_at', desc=True).execute()
    return result.data

@router.get("/sentiment/overview")
async def get_sentiment_overview(current_user: TokenData = Depends(get_current_user)):
    if not current_user.politician_id:
        raise HTTPException(status_code=403, detail="User not associated with a politician")
    
    supabase = get_supabase()
    all_data = supabase.table('sentiment_analytics').select('sentiment_score, issue_category').eq('politician_id', current_user.politician_id).execute()
    
    if not all_data.data:
        return {
            "average_sentiment": 0,
            "total_mentions": 0,
            "issue_distribution": {}
        }
    
    scores = [entry['sentiment_score'] for entry in all_data.data]
    avg_sentiment = sum(scores) / len(scores) if scores else 0
    
    issue_counts = {}
    for entry in all_data.data:
        category = entry['issue_category']
        issue_counts[category] = issue_counts.get(category, 0) + 1
    
    return {
        "average_sentiment": round(avg_sentiment, 2),
        "total_mentions": len(all_data.data),
        "issue_distribution": issue_counts
    }

@router.get("/dashboard")
async def get_dashboard_stats(current_user: TokenData = Depends(get_current_user)):
    if not current_user.politician_id:
        raise HTTPException(status_code=403, detail="User not associated with a politician")
    
    supabase = get_supabase()
    
    grievances = supabase.table('grievances').select('status').eq('politician_id', current_user.politician_id).execute()
    posts = supabase.table('posts').select('status').eq('politician_id', current_user.politician_id).execute()
    
    resolved_grievances = len([g for g in grievances.data if g['status'] == 'resolved'])
    published_posts = len([p for p in posts.data if p['status'] == 'published'])
    
    return {
        "total_grievances": len(grievances.data),
        "resolved_grievances": resolved_grievances,
        "total_posts": len(posts.data),
        "published_posts": published_posts
    }