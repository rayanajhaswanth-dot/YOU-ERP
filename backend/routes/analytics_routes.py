from fastapi import APIRouter, HTTPException, Depends
from auth import get_current_user, TokenData
from database import get_supabase
import os
import requests
import asyncio
from typing import List
import sys
sys.path.append('/app/backend')
from services.sentiment_engine import analyze_social_sentiment, calculate_ground_stability

router = APIRouter()

# 11 OFFICIAL CATEGORIES (ENGLISH ONLY)
OFFICIAL_CATEGORIES = [
    "Water & Irrigation",
    "Agriculture", 
    "Forests & Environment",
    "Health & Sanitation",
    "Education",
    "Infrastructure & Roads",
    "Law & Order",
    "Welfare Schemes",
    "Finance & Taxation",
    "Urban & Rural Development",
    "Electricity",
    "Miscellaneous"
]

def normalize_category(category: str) -> str:
    """Normalize any category string to official English category"""
    if not category:
        return "Miscellaneous"
    
    # Direct match
    if category in OFFICIAL_CATEGORIES:
        return category
    
    # Case-insensitive match
    for official in OFFICIAL_CATEGORIES:
        if category.lower() == official.lower():
            return official
    
    # Keyword mapping for legacy/non-standard categories
    category_lower = category.lower()
    
    mappings = {
        "water": "Water & Irrigation",
        "irrigation": "Water & Irrigation",
        "agriculture": "Agriculture",
        "farming": "Agriculture",
        "health": "Health & Sanitation",
        "sanitation": "Health & Sanitation",
        "hospital": "Health & Sanitation",
        "education": "Education",
        "school": "Education",
        "road": "Infrastructure & Roads",
        "infrastructure": "Infrastructure & Roads",
        "law": "Law & Order",
        "police": "Law & Order",
        "welfare": "Welfare Schemes",
        "pension": "Welfare Schemes",
        "electricity": "Electricity",
        "power": "Electricity",
        "forest": "Forests & Environment",
        "environment": "Forests & Environment",
        "tax": "Finance & Taxation",
        "urban": "Urban & Rural Development",
        "rural": "Urban & Rural Development",
        "general": "Miscellaneous",
        "other": "Miscellaneous",
    }
    
    for key, official in mappings.items():
        if key in category_lower:
            return official
    
    return "Miscellaneous"

# Global Configuration
FB_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
IG_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")


async def fetch_facebook_data():
    if not FB_PAGE_ACCESS_TOKEN or not FB_PAGE_ID:
        return []
    
    try:
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
        params = {
            "access_token": FB_PAGE_ACCESS_TOKEN,
            "fields": "id,message,created_time,insights.metric(post_impressions_unique,post_reactions_by_type_total,post_comments)",
            "limit": 10
        }
        response = await asyncio.to_thread(requests.get, url, params=params)
        if response.status_code != 200:
            print(f"❌ [FB Analytics] Error: {response.text}")
            return []
            
        data = response.json()
        processed_posts = []
        
        for post in data.get("data", []):
            message = post.get("message", "Media Update")
            insights = post.get("insights", {}).get("data", [])
            
            reach = 0
            likes = 0
            comments = 0
            
            for metric in insights:
                if metric["name"] == "post_impressions_unique":
                    reach = metric["values"][0]["value"]
                if metric["name"] == "post_reactions_by_type_total":
                    # FB returns reactions as a map, we sum them for 'likes' equivalent
                    reactions = metric["values"][0]["value"]
                    likes = sum(reactions.values())
                if metric["name"] == "post_comments":
                    # Some FB metrics differ, but we try standard
                    pass 

            processed_posts.append({
                "id": post["id"],
                "platform": "facebook",
                "content": message[:60] + "..." if len(message) > 60 else message,
                "date": post["created_time"],
                "reach": reach,
                "likes": likes,
                "comments": comments,
                "engagement": likes + comments,
                "url": f"https://facebook.com/{post['id']}"
            })
        
        print(f"✅ [FB Analytics] Fetched {len(processed_posts)} posts with reactions")
        return processed_posts
    except Exception as e:
        print(f"❌ [FB Analytics] Exception: {e}")
        return []


async def fetch_instagram_data():
    if not FB_PAGE_ACCESS_TOKEN or not IG_ACCOUNT_ID:
        print("⚠️ [IG Analytics] Missing Credentials.")
        return []

    processed_posts = []

    try:
        # STAGE 1: Fetch Basic Media Data (Robust)
        url = f"https://graph.facebook.com/v18.0/{IG_ACCOUNT_ID}/media"
        params = {
            "access_token": FB_PAGE_ACCESS_TOKEN,
            "fields": "id,caption,timestamp,media_type,permalink,like_count,comments_count",
            "limit": 10
        }
        
        response = await asyncio.to_thread(requests.get, url, params=params)
        
        if response.status_code != 200:
            print(f"❌ [IG Analytics] List Fetch Failed: {response.text}")
            return []

        data = response.json()
        print(f"📸 [IG Analytics] Fetched {len(data.get('data', []))} posts")
        
        # STAGE 2: Process & Enrich
        for post in data.get("data", []):
            post_id = post.get("id")
            reach = 0
            
            # Safe Integer Conversion
            likes = int(post.get("like_count", 0) or 0)
            comments = int(post.get("comments_count", 0) or 0)
            
            # Try to fetch Reach separately (Best Effort)
            try:
                insights_url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
                insights_params = {
                    "access_token": FB_PAGE_ACCESS_TOKEN,
                    "metric": "reach",
                    "period": "lifetime"
                }
                
                insights_res = await asyncio.to_thread(requests.get, insights_url, params=insights_params)
                
                if insights_res.status_code == 200:
                    ins_data = insights_res.json().get("data", [])
                    for metric in ins_data:
                        if metric["name"] == "reach":
                            reach = metric["values"][0]["value"]
            except Exception as e:
                # Silently fail on insights (permissions) but keep the post
                pass

            raw_caption = post.get("caption") or "Instagram Media"
            clean_caption = raw_caption[:60] + "..." if len(raw_caption) > 60 else raw_caption

            processed_posts.append({
                "id": post_id,
                "platform": "instagram",
                "content": clean_caption,
                "date": post.get("timestamp"),
                "reach": reach,
                "likes": likes,
                "comments": comments,
                "engagement": likes + comments,
                "url": post.get("permalink", "#")
            })
        
        print(f"✅ [IG Analytics] Processed {len(processed_posts)} posts with likes/comments")
        return processed_posts

    except Exception as e:
        print(f"❌ [IG Analytics] Critical Exception: {e}")
        return []


async def fetch_social_media_sentiment():
    """
    Fetch comments/reactions from Meta API and analyze sentiment.
    """
    if not FB_PAGE_ACCESS_TOKEN or not FB_PAGE_ID:
        return {
            "positive": 0,
            "neutral": 0,
            "negative": 0,
            "overall": "Neutral",
            "summary": "Social media not connected."
        }
    
    try:
        # Fetch recent posts with comments
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/posts"
        params = {
            "access_token": FB_PAGE_ACCESS_TOKEN,
            "fields": "id,message,created_time,comments{message},reactions.summary(total_count).type(LIKE),reactions.summary(total_count).type(LOVE),reactions.summary(total_count).type(HAHA),reactions.summary(total_count).type(WOW),reactions.summary(total_count).type(SAD),reactions.summary(total_count).type(ANGRY)",
            "limit": 5
        }
        
        response = await asyncio.to_thread(requests.get, url, params=params)
        
        if response.status_code != 200:
            print(f"❌ [Sentiment] Failed to fetch posts: {response.text}")
            return {"positive": 0, "neutral": 0, "negative": 0, "overall": "Neutral", "summary": "API error"}
        
        data = response.json()
        posts = data.get("data", [])
        
        all_comments = []
        total_reactions = {"like": 0, "love": 0, "haha": 0, "wow": 0, "sad": 0, "angry": 0}
        post_context = ""
        
        for post in posts:
            # Collect comments
            comments_data = post.get("comments", {}).get("data", [])
            for c in comments_data:
                all_comments.append(c.get("message", ""))
            
            # Get post context
            if not post_context:
                post_context = post.get("message", "Political post")[:200]
        
        # Use sentiment engine
        sentiment_result = await analyze_social_sentiment(post_context, all_comments, total_reactions)
        
        return {
            "positive": sentiment_result.get("positive_count", 0),
            "neutral": sentiment_result.get("neutral_count", 0),
            "negative": sentiment_result.get("negative_count", 0),
            "overall": sentiment_result.get("overall_sentiment", "Neutral"),
            "summary": sentiment_result.get("narrative_summary", "")
        }
        
    except Exception as e:
        print(f"❌ [Sentiment] Exception: {e}")
        return {"positive": 0, "neutral": 0, "negative": 0, "overall": "Neutral", "summary": str(e)}


@router.get("/happiness_metrics")
async def get_happiness_metrics(user: TokenData = Depends(get_current_user)):
    """
    Comprehensive Happiness Report metrics combining:
    1. Ground Stability (SLA-based grievance resolution)
    2. Digital Sentiment (Social media analysis)
    3. Citizen Feedback (Star ratings)
    """
    user_role = user.role.lower() if user.role else "citizen"
    if user_role not in ["leader", "osd", "politician"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    
    supabase = get_supabase()
    
    # Fetch grievances for ground stability
    try:
        grievances_result = supabase.table('grievances').select('*').eq('politician_id', user.politician_id).execute()
        grievances = grievances_result.data or []
    except Exception as e:
        print(f"❌ [Happiness] Grievance fetch error: {e}")
        grievances = []
    
    # Calculate ground stability (SLA metrics)
    ground_metrics = calculate_ground_stability(grievances)
    
    # Fetch digital sentiment
    digital_sentiment = await fetch_social_media_sentiment()
    
    # Calculate overall happiness score (0-100)
    sla_score = ground_metrics.get("sla_percentage", 0)
    rating_score = (ground_metrics.get("citizen_rating", 0) / 5) * 100  # Convert 5-star to percentage
    
    # Weight: 60% SLA, 40% Rating
    overall_score = (sla_score * 0.6) + (rating_score * 0.4) if rating_score > 0 else sla_score
    
    return {
        "overall_score": round(overall_score, 1),
        "ground": {
            "total_grievances": ground_metrics.get("total", 0),
            "resolved": ground_metrics.get("resolved", 0),
            "resolved_within_sla": ground_metrics.get("resolved_within_sla", 0),
            "sla_percentage": round(ground_metrics.get("sla_percentage", 0), 1),
            "status_label": ground_metrics.get("status_label", "No Data"),
            "citizen_rating": round(ground_metrics.get("citizen_rating", 0), 1),
            "rating_count": ground_metrics.get("rating_count", 0)
        },
        "digital": {
            "positive": digital_sentiment.get("positive", 0),
            "neutral": digital_sentiment.get("neutral", 0),
            "negative": digital_sentiment.get("negative", 0),
            "overall_sentiment": digital_sentiment.get("overall", "Neutral"),
            "narrative": digital_sentiment.get("summary", "")
        }
    }


@router.get("/campaigns")
async def get_campaign_performance(user: TokenData = Depends(get_current_user)):
    user_role = user.role.lower() if user.role else "citizen"
    if user_role not in ["leader", "osd", "politician"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    fb_data, ig_data = await asyncio.gather(fetch_facebook_data(), fetch_instagram_data())
    
    all_posts = fb_data + ig_data
    all_posts.sort(key=lambda x: x["date"], reverse=True)

    total_reach = sum(p["reach"] for p in all_posts)
    total_engagement = sum(p["engagement"] for p in all_posts)
    
    return {
        "summary": {
            "total_reach": total_reach,
            "total_engagement": total_engagement,
            "platform_breakdown": {
                "facebook": len(fb_data),
                "instagram": len(ig_data)
            }
        },
        "posts": all_posts[:20]
    }


@router.get("/grievance-stats")
async def get_grievance_stats(user: TokenData = Depends(get_current_user)):
    """
    Get grievance statistics with NORMALIZED English categories.
    This endpoint ensures graphs display only the 11 official categories.
    """
    user_role = user.role.lower() if user.role else "citizen"
    if user_role not in ["leader", "osd", "politician"]:
        raise HTTPException(status_code=403, detail="Access denied.")
    
    supabase = get_supabase()
    
    try:
        grievances_result = supabase.table('grievances').select('*').eq('politician_id', user.politician_id).execute()
        grievances = grievances_result.data or []
    except Exception as e:
        print(f"❌ [Analytics] Grievance fetch error: {e}")
        grievances = []
    
    # Aggregate by NORMALIZED English category
    category_counts = {cat: 0 for cat in OFFICIAL_CATEGORIES}
    status_counts = {"PENDING": 0, "IN_PROGRESS": 0, "RESOLVED": 0, "ASSIGNED": 0}
    priority_counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
    
    for g in grievances:
        # Normalize category to official English
        raw_category = g.get('category') or g.get('issue_type') or 'Miscellaneous'
        normalized = normalize_category(raw_category)
        category_counts[normalized] = category_counts.get(normalized, 0) + 1
        
        # Count by status
        status = (g.get('status') or 'PENDING').upper()
        if status in status_counts:
            status_counts[status] += 1
        
        # Count by priority
        priority = (g.get('priority_level') or 'LOW').upper()
        if priority in priority_counts:
            priority_counts[priority] += 1
    
    # Format for charts (sorted by count)
    category_chart_data = [
        {"name": cat, "count": count}
        for cat, count in sorted(category_counts.items(), key=lambda x: -x[1])
        if count > 0
    ]
    
    return {
        "total": len(grievances),
        "by_category": category_chart_data,
        "by_status": status_counts,
        "by_priority": priority_counts,
        "categories": OFFICIAL_CATEGORIES
    }

