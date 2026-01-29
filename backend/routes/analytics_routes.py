from fastapi import APIRouter, HTTPException, Depends
from auth import get_current_user, TokenData
import os
import requests
import asyncio
from typing import List

router = APIRouter()

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
            "fields": "id,message,created_time,insights.metric(post_impressions_unique,post_engagements),permalink_url",
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
            engagement = 0
            
            for metric in insights:
                if metric["name"] == "post_impressions_unique":
                    reach = metric["values"][0]["value"]
                if metric["name"] == "post_engagements":
                    engagement = metric["values"][0]["value"]

            processed_posts.append({
                "id": post["id"],
                "platform": "facebook",
                "content": message[:60] + "..." if len(message) > 60 else message,
                "date": post["created_time"],
                "reach": reach,
                "engagement": engagement,
                "url": post.get("permalink_url", "#")
            })
        
        print(f"✅ [FB Analytics] Fetched {len(processed_posts)} posts")
        return processed_posts
    except Exception as e:
        print(f"❌ [FB Analytics] Exception: {e}")
        return []

async def fetch_instagram_data():
    if not FB_PAGE_ACCESS_TOKEN or not IG_ACCOUNT_ID:
        print("⚠️ [IG Analytics] Missing Credentials.")
        return []

    processed_posts = []
    url = f"https://graph.facebook.com/v18.0/{IG_ACCOUNT_ID}/media"

    # Attempt 1: Fetch Media WITH Insights (Requires instagram_manage_insights)
    try:
        params = {
            "access_token": FB_PAGE_ACCESS_TOKEN,
            "fields": "id,caption,timestamp,media_type,permalink,insights.metric(impressions,reach,engagement)",
            "limit": 10
        }
        
        response = await asyncio.to_thread(requests.get, url, params=params)
        
        if response.status_code == 200:
            data = response.json()
            for post in data.get("data", []):
                processed_posts.append(parse_ig_post(post, has_metrics=True))
            print(f"✅ [IG Analytics] Fetched {len(processed_posts)} posts with insights")
            return processed_posts
        else:
            print(f"⚠️ [IG Analytics] Insights fetch failed ({response.status_code}). Trying fallback...")
            # If 400/403, proceed to fallback
            
    except Exception as e:
        print(f"❌ [IG Analytics] Insights Exception: {e}")

    # Attempt 2: Fallback to Basic Media (Requires only instagram_basic)
    # This ensures users at least see their posts even if metrics fail.
    try:
        print("🔄 [IG Analytics] Attempting Fallback (Basic Media Only)...")
        fallback_params = {
            "access_token": FB_PAGE_ACCESS_TOKEN,
            "fields": "id,caption,timestamp,media_type,permalink",
            "limit": 10
        }
        response = await asyncio.to_thread(requests.get, url, params=fallback_params)
        
        if response.status_code == 200:
            data = response.json()
            for post in data.get("data", []):
                processed_posts.append(parse_ig_post(post, has_metrics=False))
            print(f"✅ [IG Analytics] Fallback Successful ({len(processed_posts)} posts). Note: Metrics are 0 due to missing permissions.")
            return processed_posts
        else:
            print(f"❌ [IG Analytics] Fallback failed: {response.text}")
            return []
            
    except Exception as e:
        print(f"❌ [IG Analytics] Fallback Exception: {e}")
        return []

def parse_ig_post(post, has_metrics=True):
    """Helper to parse IG post data safely"""
    caption = post.get("caption", "Instagram Media")
    reach = 0
    engagement = 0
    
    if has_metrics:
        insights = post.get("insights", {}).get("data", [])
        for metric in insights:
            if metric["name"] == "reach":
                reach = metric["values"][0]["value"]
            elif metric["name"] == "impressions" and reach == 0:
                reach = metric["values"][0]["value"]
            if metric["name"] == "engagement":
                engagement = metric["values"][0]["value"]
    
    return {
        "id": post["id"],
        "platform": "instagram",
        "content": caption[:60] + "..." if len(caption) > 60 else caption,
        "date": post["timestamp"],
        "reach": reach,
        "engagement": engagement,
        "url": post.get("permalink", "#")
    }

@router.get("/campaigns")
async def get_campaign_performance(user: TokenData = Depends(get_current_user)):
    """
    Fetches consolidated performance metrics for Facebook AND Instagram.
    """
    user_role = user.role.lower() if user.role else "citizen"
    if user_role not in ["leader", "osd", "politician"]:
        raise HTTPException(status_code=403, detail="Access denied.")

    # Fetch both platforms in parallel
    fb_data, ig_data = await asyncio.gather(fetch_facebook_data(), fetch_instagram_data())
    
    # Merge and Sort by Date (Newest First)
    all_posts = fb_data + ig_data
    all_posts.sort(key=lambda x: x["date"], reverse=True)

    # Calculate Totals
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
        "posts": all_posts[:20]  # Return top 20 mixed
    }
