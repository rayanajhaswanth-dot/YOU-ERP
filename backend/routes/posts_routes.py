from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from typing import Optional
import os
import requests
import uuid
from auth import get_current_user, TokenData
from database import get_supabase

router = APIRouter()

# CTO CONFIG: Social Media Keys
# Ensure these are in your .env file
FB_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")

@router.post("/publish")
async def publish_post(
    content: str = Form(...),
    platform: str = Form(...),
    image: Optional[UploadFile] = File(None),
    user: TokenData = Depends(get_current_user)
):
    """
    Directly publishes content to Social Media APIs.
    Supports Text + Image for Facebook.
    """
    # 1. Permission Check (RBAC)
    user_role = user.role.lower() if user.role else "citizen"
    if user_role not in ["leader", "osd", "politician"]:
        raise HTTPException(status_code=403, detail="Not authorized to publish content.")

    image_url = None
    supabase = get_supabase()

    # 2. Image Handling (Upload to Supabase Storage)
    if image:
        try:
            # Generate unique filename
            file_ext = image.filename.split(".")[-1]
            file_name = f"{uuid.uuid4()}.{file_ext}"
            file_content = await image.read()
            
            # Upload to 'campaign-assets' bucket
            # Note: User must create this bucket in Supabase Storage and make it Public
            supabase.storage.from_("campaign-assets").upload(file_name, file_content)
            
            # Construct Public URL
            project_url = os.getenv("SUPABASE_URL") 
            # Clean up URL if it has /rest/v1
            base_url = project_url.replace("/rest/v1", "") if project_url else ""
            image_url = f"{base_url}/storage/v1/object/public/campaign-assets/{file_name}"
            print(f"✅ Image uploaded to Supabase: {image_url}")
            
        except Exception as e:
            print(f"⚠️ Image Upload Error: {e}")
            # We proceed without image if upload fails to at least get text out
            pass

    # 3. Facebook Logic
    if platform == 'facebook':
        if not FB_PAGE_ACCESS_TOKEN or not FB_PAGE_ID:
            raise HTTPException(status_code=503, detail="Facebook credentials missing. Use Manual Posting.")
        
        # Endpoint Selection: Photos vs Feed
        if image_url:
            url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
            payload = {
                "message": content,
                "url": image_url,
                "access_token": FB_PAGE_ACCESS_TOKEN
            }
        else:
            url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
            payload = {
                "message": content,
                "access_token": FB_PAGE_ACCESS_TOKEN
            }
        
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            print(f"✅ Published to Facebook: {response.json()}")
            return {
                "status": "published", 
                "platform": "facebook", 
                "post_id": response.json().get("id"),
                "image_url": image_url
            }
        except requests.exceptions.RequestException as e:
            print(f"❌ Meta API Error: {e}")
            raise HTTPException(status_code=500, detail=f"Meta API Failed: {str(e)}")

    return {"status": "skipped", "message": "Platform logic handled on client"}
