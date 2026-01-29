from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from database import get_supabase
from auth import get_current_user, TokenData
from datetime import datetime, timezone, timedelta
import uuid
import os
import requests

router = APIRouter()

# CTO CONFIG: Social Media Keys for Campaign Analytics
FB_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")

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
    
    try:
        result = supabase.table('sentiment_analytics').select('*').eq('politician_id', current_user.politician_id).gte('created_at', start_date).order('created_at', desc=True).execute()
        return result.data
    except Exception as e:
        # Return empty list if table doesn't exist
        if 'PGRST205' in str(e) or 'sentiment_analytics' in str(e).lower():
            return []
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sentiment/overview")
async def get_sentiment_overview(current_user: TokenData = Depends(get_current_user)):
    if not current_user.politician_id:
        raise HTTPException(status_code=403, detail="User not associated with a politician")
    
    supabase = get_supabase()
    try:
        all_data = supabase.table('sentiment_analytics').select('sentiment_score, issue_category').eq('politician_id', current_user.politician_id).execute()
    except Exception as e:
        # Return empty data if table doesn't exist
        if 'PGRST205' in str(e) or 'sentiment_analytics' in str(e).lower():
            return {
                "average_sentiment": 0,
                "total_mentions": 0,
                "issue_distribution": {}
            }
        raise HTTPException(status_code=500, detail=str(e))
    
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
    
    try:
        grievances = supabase.table('grievances').select('status').eq('politician_id', current_user.politician_id).execute()
    except:
        grievances = type('obj', (object,), {'data': []})()
    
    try:
        posts = supabase.table('posts').select('status').eq('politician_id', current_user.politician_id).execute()
    except:
        posts = type('obj', (object,), {'data': []})()
    
    resolved_grievances = len([g for g in grievances.data if g.get('status', '').upper() == 'RESOLVED'])
    published_posts = len([p for p in posts.data if p.get('status', '').upper() == 'PUBLISHED'])
    
    return {
        "total_grievances": len(grievances.data),
        "resolved_grievances": resolved_grievances,
        "total_posts": len(posts.data),
        "published_posts": published_posts
    }


@router.get("/campaigns")
async def get_campaign_performance(user: TokenData = Depends(get_current_user)):
    """
    Fetches performance metrics for recent social media posts.
    Currently supports: Facebook Page Feed.
    """
    
    # 1. RBAC Security Check
    user_role = user.role.lower() if user.role else "citizen"
    if user_role not in ["leader", "osd", "politician"]:
        raise HTTPException(status_code=403, detail="Access denied to Intelligence Data.")

    if not FB_PAGE_ACCESS_TOKEN or not FB_PAGE_ID:
        # Graceful degradation if keys are missing (for dev environment)
        return {
            "summary": {"total_reach": 0, "total_engagement": 0},
            "posts": []
        }

    try:
        # 2. Query Meta Graph API for Posts + Insights
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
        params = {
            "access_token": FB_PAGE_ACCESS_TOKEN,
            "fields": "id,message,created_time,insights.metric(post_impressions_unique,post_engagements),permalink_url",
            "limit": 10  # Last 10 posts
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        
        posts_data = []
        total_reach = 0
        total_engagement = 0

        # 3. Process the Data
        for post in data.get("data", []):
            message = post.get("message", "Media Update")
            
            # Extract Insights safely
            insights = post.get("insights", {}).get("data", [])
            
            reach = 0
            engagement = 0
            
            for metric in insights:
                if metric["name"] == "post_impressions_unique":
                    reach = metric["values"][0]["value"]
                if metric["name"] == "post_engagements":
                    engagement = metric["values"][0]["value"]
            
            total_reach += reach
            total_engagement += engagement

            posts_data.append({
                "id": post["id"],
                "platform": "facebook",
                "content": message[:50] + "..." if len(message) > 50 else message,
                "date": post["created_time"],
                "reach": reach,
                "engagement": engagement,
                "url": post.get("permalink_url", "#")
            })

        print(f"✅ Campaign Analytics: Fetched {len(posts_data)} posts")
        return {
            "summary": {
                "total_reach": total_reach,
                "total_engagement": total_engagement,
                "platform_breakdown": {"facebook": len(posts_data)}
            },
            "posts": posts_data
        }

    except Exception as e:
        print(f"❌ Analytics Error: {str(e)}")
        # Don't crash the dashboard, return empty state with error flag
        return {
            "error": "Could not fetch live data from Meta.",
            "details": str(e),
            "posts": []
        }