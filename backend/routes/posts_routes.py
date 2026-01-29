from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from typing import Optional
import os
import requests
import uuid
from auth import get_current_user, TokenData
from database import get_supabase

router = APIRouter()

# CTO CONFIG: Social Media Keys
FB_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
IG_ACCOUNT_ID = os.getenv("INSTAGRAM_ACCOUNT_ID")

@router.post("/publish")
async def publish_post(
    content: str = Form(...),
    platform: str = Form(...),
    image: Optional[UploadFile] = File(None),
    user: TokenData = Depends(get_current_user)
):
    """
    Directly publishes content to Social Media APIs.
    """
    # 1. Permission Check
    user_role = user.role.lower() if user.role else "citizen"
    if user_role not in ["leader", "osd", "politician"]:
        raise HTTPException(status_code=403, detail="Not authorized to publish content.")

    image_url = None
    supabase = get_supabase()

    # 2. Image Handling
    if image:
        try:
            file_ext = image.filename.split(".")[-1]
            file_name = f"{uuid.uuid4()}.{file_ext}"
            file_content = await image.read()
            supabase.storage.from_("campaign-assets").upload(file_name, file_content)
            project_url = os.getenv("SUPABASE_URL") 
            base_url = project_url.replace("/rest/v1", "") if project_url else ""
            image_url = f"{base_url}/storage/v1/object/public/campaign-assets/{file_name}"
            print(f"✅ Image uploaded: {image_url}")
        except Exception as e:
            print(f"⚠️ Image Upload Warning: {e}")
            pass

    # 3. Facebook Logic
    if platform == 'facebook':
        if not FB_PAGE_ACCESS_TOKEN or not FB_PAGE_ID:
            raise HTTPException(status_code=503, detail="Facebook credentials missing in .env")
        
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
            # Extract detailed error from Meta
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_msg = e.response.json().get('error', {}).get('message', str(e))
                except:
                    pass
            print(f"❌ FB Error: {error_msg}")
            raise HTTPException(status_code=400, detail=f"Facebook API Error: {error_msg}")

    # 4. Instagram Logic
    if platform == 'instagram':
        if not IG_ACCOUNT_ID:
            raise HTTPException(status_code=503, detail="Instagram Account ID missing in .env")
        if not image_url:
             raise HTTPException(status_code=400, detail="Instagram requires an image.")

        try:
            # Step A: Container
            container_url = f"https://graph.facebook.com/v18.0/{IG_ACCOUNT_ID}/media"
            container_payload = { "image_url": image_url, "caption": content, "access_token": FB_PAGE_ACCESS_TOKEN }
            print(f"📸 Creating Instagram container...")
            c_res = requests.post(container_url, data=container_payload)
            c_res.raise_for_status()
            creation_id = c_res.json().get("id")
            print(f"✅ Container created: {creation_id}")

            # Step B: Publish
            p_url = f"https://graph.facebook.com/v18.0/{IG_ACCOUNT_ID}/media_publish"
            p_payload = { "creation_id": creation_id, "access_token": FB_PAGE_ACCESS_TOKEN }
            print(f"📤 Publishing to Instagram...")
            p_res = requests.post(p_url, data=p_payload)
            p_res.raise_for_status()
            
            print(f"✅ Published to Instagram: {p_res.json()}")
            return {"status": "published", "platform": "instagram", "post_id": p_res.json().get("id")}

        except requests.exceptions.RequestException as e:
            # Extract detailed error from Meta
            error_msg = str(e)
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_msg = e.response.json().get('error', {}).get('message', str(e))
                except:
                    pass
            print(f"❌ IG Error: {error_msg}")
            raise HTTPException(status_code=400, detail=f"Instagram API Error: {error_msg}")

    return {"status": "skipped", "message": "Platform logic handled on client"}
