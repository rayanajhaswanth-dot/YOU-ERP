from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from typing import Optional
import os
import requests
import uuid
import time
from auth import get_current_user, TokenData
from database import get_supabase

router = APIRouter()

# CTO CONFIG: Social Media Keys
# Ensure these are in your .env file
FB_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
IG_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")  # New Config for Instagram

@router.post("/publish")
async def publish_post(
    content: str = Form(...),
    platform: str = Form(...),
    image: Optional[UploadFile] = File(None),
    user: TokenData = Depends(get_current_user)
):
    """
    Directly publishes content to Social Media APIs.
    Supports Facebook (Feed/Photos) and Instagram (Media Publish).
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
            supabase.storage.from_("campaign-assets").upload(file_name, file_content)
            
            # Construct Public URL
            project_url = os.getenv("SUPABASE_URL") 
            base_url = project_url.replace("/rest/v1", "") if project_url else ""
            image_url = f"{base_url}/storage/v1/object/public/campaign-assets/{file_name}"
            print(f"✅ Image uploaded: {image_url}")
            
        except Exception as e:
            print(f"⚠️ Image Upload Error: {e}")
            pass

    # 3. Facebook Logic
    if platform == 'facebook':
        if not FB_PAGE_ACCESS_TOKEN or not FB_PAGE_ID:
            raise HTTPException(status_code=503, detail="Facebook credentials missing.")
        
        if image_url:
            url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/photos"
            payload = { "message": content, "url": image_url, "access_token": FB_PAGE_ACCESS_TOKEN }
        else:
            url = f"https://graph.facebook.com/v18.0/{FB_PAGE_ID}/feed"
            payload = { "message": content, "access_token": FB_PAGE_ACCESS_TOKEN }
        
        try:
            response = requests.post(url, data=payload)
            response.raise_for_status()
            print(f"✅ Published to Facebook: {response.json()}")
            return {"status": "published", "platform": "facebook", "post_id": response.json().get("id")}
        except requests.exceptions.RequestException as e:
            print(f"❌ Facebook API Error: {e}")
            raise HTTPException(status_code=500, detail=f"Facebook API Failed: {str(e)}")

    # 4. Instagram Logic (Two-Step: Container -> Publish)
    if platform == 'instagram':
        if not FB_PAGE_ACCESS_TOKEN or not IG_ACCOUNT_ID:
            raise HTTPException(status_code=503, detail="Instagram credentials missing (Need INSTAGRAM_ACCOUNT_ID).")
        
        if not image_url:
             raise HTTPException(status_code=400, detail="Instagram requires an image. Please upload one.")

        try:
            # Step A: Create Media Container
            container_url = f"https://graph.facebook.com/v18.0/{IG_ACCOUNT_ID}/media"
            container_payload = {
                "image_url": image_url,
                "caption": content,
                "access_token": FB_PAGE_ACCESS_TOKEN
            }
            print(f"📸 Creating Instagram container...")
            container_res = requests.post(container_url, data=container_payload)
            container_res.raise_for_status()
            creation_id = container_res.json().get("id")
            print(f"✅ Container created: {creation_id}")

            # Step B: Publish Media
            # (Small delay sometimes helps with API processing)
            time.sleep(1)
            
            publish_url = f"https://graph.facebook.com/v18.0/{IG_ACCOUNT_ID}/media_publish"
            publish_payload = {
                "creation_id": creation_id,
                "access_token": FB_PAGE_ACCESS_TOKEN
            }
            print(f"📤 Publishing to Instagram...")
            publish_res = requests.post(publish_url, data=publish_payload)
            publish_res.raise_for_status()
            
            print(f"✅ Published to Instagram: {publish_res.json()}")
            return {"status": "published", "platform": "instagram", "post_id": publish_res.json().get("id")}

        except requests.exceptions.RequestException as e:
            print(f"❌ Instagram API Error: {e}")
            # Extract detailed error message from Meta API
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_data = e.response.json()
                    error_msg = error_data.get('error', {}).get('message', str(e))
                except:
                    pass
            raise HTTPException(status_code=500, detail=f"Instagram API Failed: {error_msg}")

    return {"status": "skipped", "message": "Platform logic handled on client"}
