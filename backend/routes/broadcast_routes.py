from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import os
import requests
from auth import get_current_user, TokenData

router = APIRouter()

# CTO CONFIG: Social Media Keys
# Ensure these are in your .env file
FB_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")

class PostRequest(BaseModel):
    content: str
    platform: str  # 'facebook', 'instagram'

@router.post("/publish")
async def publish_post(request: PostRequest, user: TokenData = Depends(get_current_user)):
    """
    Directly publishes content to Social Media APIs.
    Currently supports: Facebook Page Feed.
    """
    # 1. Permission Check (Optional: Only Leader/OSD can post)
    user_role = user.role.lower() if user.role else "citizen"
    if user_role not in ["leader", "osd", "politician"]:
        raise HTTPException(status_code=403, detail="Not authorized to publish content.")

    # 2. Facebook Logic
    if request.platform == 'facebook':
        if not FB_PAGE_ACCESS_TOKEN or not FB_PAGE_ID:
             # Soft Fail: If keys aren't there, tell Frontend to use Clipboard fallback
            raise HTTPException(status_code=503, detail="Facebook credentials missing. Use Manual Posting.")
        
        url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
        payload = {
            "message": request.content,
            "access_token": FB_PAGE_ACCESS_TOKEN
        }
        
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status() # Raise error for 4xx/5xx
            
            return {
                "status": "published", 
                "platform": "facebook",
                "post_id": response.json().get("id")
            }
        except requests.exceptions.RequestException as e:
            print(f"Meta API Error: {e}")
            raise HTTPException(status_code=500, detail=f"Meta API Failed: {str(e)}")

    # 3. Instagram Logic (Placeholder - requires Image)
    if request.platform == 'instagram':
        # Instagram Graph API requires an Image URL. Text-only is not supported.
        return {"status": "skipped", "message": "Instagram requires an image. Please use mobile app."}

    return {"status": "error", "message": "Platform not supported"}
