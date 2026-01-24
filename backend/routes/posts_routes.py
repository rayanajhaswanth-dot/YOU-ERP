from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from database import get_supabase
from auth import get_current_user, TokenData
from datetime import datetime, timezone
import uuid

router = APIRouter()

class PostCreate(BaseModel):
    content: str
    platforms: List[str]
    scheduled_at: Optional[str] = None

class PostUpdate(BaseModel):
    status: Optional[str] = None
    content: Optional[str] = None

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
    try:
        query = supabase.table('posts').select('*').eq('politician_id', current_user.politician_id)
        
        if status:
            query = query.eq('status', status)
        
        result = query.order('created_at', desc=True).execute()
        return result.data
    except Exception as e:
        # Return empty list if table doesn't exist
        if 'PGRST205' in str(e) or 'posts' in str(e).lower():
            return []
        raise HTTPException(status_code=500, detail=str(e))

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
        if data.status == 'published':
            update_data['published_at'] = datetime.now(timezone.utc).isoformat()
    if data.content:
        update_data['content'] = data.content
    
    result = supabase.table('posts').update(update_data).eq('id', post_id).execute()
    return {"message": "Post updated successfully"}

@router.post("/{post_id}/approve")
async def approve_post(
    post_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    if current_user.role != 'politician':
        raise HTTPException(status_code=403, detail="Only politicians can approve posts")
    
    supabase = get_supabase()
    
    existing = supabase.table('posts').select('*').eq('id', post_id).eq('politician_id', current_user.politician_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Post not found")
    
    update_data = {
        'status': 'approved',
        'approved_by': current_user.user_id,
        'approved_at': datetime.now(timezone.utc).isoformat()
    }
    
    result = supabase.table('posts').update(update_data).eq('id', post_id).execute()
    return {"message": "Post approved successfully"}