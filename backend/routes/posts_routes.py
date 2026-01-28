from fastapi import APIRouter, HTTPException, Depends, File, UploadFile, Form
from pydantic import BaseModel
from typing import Optional, List
from database import get_supabase
from auth import get_current_user, TokenData
from datetime import datetime, timezone
import os
import requests
import uuid

router = APIRouter()

# CTO CONFIG: Social Media Keys
FB_PAGE_ACCESS_TOKEN = os.getenv("FACEBOOK_PAGE_ACCESS_TOKEN")
FB_PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")

# Legacy models for backward compatibility
class PostCreate(BaseModel):
    content: str
    platforms: List[str]
    scheduled_at: Optional[str] = None

class PostUpdate(BaseModel):
    status: Optional[str] = None
    content: Optional[str] = None


@router.post("/publish")
async def publish_post(
    content: str = Form(...),
    platform: str = Form(...),
    image: Optional[UploadFile] = File(None),
    user: TokenData = Depends(get_current_user)
):
    """
    Publishes content with optional Image support.
    Supports: Facebook (with image via Graph API)
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
            file_ext = image.filename.split(".")[-1]
            file_name = f"{uuid.uuid4()}.{file_ext}"
            file_content = await image.read()
            
            # Upload to 'campaign-assets' bucket (Ensure this bucket exists in Supabase)
            supabase.storage.from_("campaign-assets").upload(file_name, file_content)
            
            # Get Public URL
            project_url = os.getenv("SUPABASE_URL")
            image_url = f"{project_url}/storage/v1/object/public/campaign-assets/{file_name}"
            print(f"✅ Image uploaded: {image_url}")
            
        except Exception as e:
            print(f"⚠️ Image Upload Error: {e}")
            # Continue without image if upload fails
            pass

    # 3. Facebook Logic
    if platform == 'facebook':
        if not FB_PAGE_ACCESS_TOKEN or not FB_PAGE_ID:
            raise HTTPException(status_code=503, detail="Facebook credentials missing. Use Manual Posting.")
        
        # Determine endpoint (Photos vs Feed)
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
            return {"status": "published", "platform": "facebook", "post_id": response.json().get("id"), "image_url": image_url}
        except requests.exceptions.RequestException as e:
            print(f"❌ Meta API Error: {e}")
            raise HTTPException(status_code=500, detail=f"Meta API Failed: {str(e)}")

    # 4. Fallback for others (Twitter/WA handled on client side)
    return {"status": "skipped", "message": "Platform logic handled on client", "image_url": image_url}


# ============================================================
# Legacy Endpoints (for backward compatibility)
# ============================================================

@router.post("/")
async def create_post(
    data: PostCreate,
    current_user: TokenData = Depends(get_current_user)
):
    if not current_user.politician_id:
        raise HTTPException(status_code=403, detail="User not associated with a politician")
    
    supabase = get_supabase()
    post_id = str(uuid.uuid4())
    
    post_data = {
        'id': post_id,
        'politician_id': current_user.politician_id,
        'content': data.content,
        'platforms': data.platforms,
        'status': 'draft',
        'created_by': current_user.user_id,
        'scheduled_at': data.scheduled_at,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    result = supabase.table('posts').insert(post_data).execute()
    return {"message": "Post created successfully", "id": post_id}


@router.get("/")
async def get_posts(
    status: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    if not current_user.politician_id:
        raise HTTPException(status_code=403, detail="User not associated with a politician")
    
    supabase = get_supabase()
    query = supabase.table('posts').select('*').eq('politician_id', current_user.politician_id)
    
    if status:
        query = query.eq('status', status)
    
    result = query.order('created_at', desc=True).execute()
    return result.data


@router.get("/{post_id}")
async def get_post(
    post_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    supabase = get_supabase()
    result = supabase.table('posts').select('*').eq('id', post_id).eq('politician_id', current_user.politician_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Post not found")
    
    return result.data[0]


@router.patch("/{post_id}")
async def update_post(
    post_id: str,
    data: PostUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    supabase = get_supabase()
    
    existing = supabase.table('posts').select('*').eq('id', post_id).eq('politician_id', current_user.politician_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Post not found")
    
    update_data = {}
    if data.status:
        update_data['status'] = data.status
    if data.content:
        update_data['content'] = data.content
    
    result = supabase.table('posts').update(update_data).eq('id', post_id).execute()
    return {"message": "Post updated successfully"}


@router.delete("/{post_id}")
async def delete_post(
    post_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    supabase = get_supabase()
    
    existing = supabase.table('posts').select('*').eq('id', post_id).eq('politician_id', current_user.politician_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Post not found")
    
    supabase.table('posts').delete().eq('id', post_id).execute()
    return {"message": "Post deleted successfully"}
