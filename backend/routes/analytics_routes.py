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
    """
    Robust Two-Stage Fetch for Instagram:
    1. Fetch List with Basic Stats (Likes/Comments) - Always works.
    2. Enrich with Reach/Impressions - Best effort per post.
    """
    if not FB_PAGE_ACCESS_TOKEN or not IG_ACCOUNT_ID:
        print("⚠️ [IG Analytics] Missing Credentials.")
        return []

    processed_posts = []

    try:
        # STAGE 1: Fetch Basic Media Data (Robust)
        # We assume 'instagram_basic' is working. We fetch like_count/comments_count directly.
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
        print(f"📸 [IG Analytics] Stage 1: Fetched {len(data.get('data', []))} posts")
        
        # STAGE 2: Process & Enrich
        for post in data.get("data", []):
            post_id = post.get("id")
            reach = 0
            
            # Engagement Fallback: Calculate manually (Likes + Comments)
            # This guarantees we show metrics even if the Insights API fails.
            likes = post.get("like_count", 0)
            comments = post.get("comments_count", 0)
            engagement = likes + comments

            # Try to fetch Reach separately (Best Effort)
            try:
                insights_url = f"https://graph.facebook.com/v18.0/{post_id}/insights"
                insights_params = {
                    "access_token": FB_PAGE_ACCESS_TOKEN,
                    "metric": "reach,impressions",
                    "period": "lifetime"
                }
                
                insights_res = await asyncio.to_thread(requests.get, insights_url, params=insights_params)
                
                if insights_res.status_code == 200:
                    ins_data = insights_res.json().get("data", [])
                    for metric in ins_data:
                        if metric["name"] == "reach":
                            reach = metric["values"][0]["value"]
                        elif metric["name"] == "impressions" and reach == 0:
                            reach = metric["values"][0]["value"]
                else:
                    # Log silently, don't crash.
                    pass
            except Exception as e:
                print(f"⚠️ [IG Analytics] Insight Error for {post_id}: {e}")

            # Safe Caption Handling
            raw_caption = post.get("caption") or "Instagram Media"
            clean_caption = raw_caption[:60] + "..." if len(raw_caption) > 60 else raw_caption

            processed_posts.append({
                "id": post_id,
                "platform": "instagram",
                "content": clean_caption,
                "date": post.get("timestamp"),
                "reach": reach,
                "engagement": engagement,
                "url": post.get("permalink", "#")
            })
        
        print(f"✅ [IG Analytics] Stage 2: Processed {len(processed_posts)} posts with engagement data")
        return processed_posts

    except Exception as e:
        print(f"❌ [IG Analytics] Critical Exception: {e}")
        return []

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
