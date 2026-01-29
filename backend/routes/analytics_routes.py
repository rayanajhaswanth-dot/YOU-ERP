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
