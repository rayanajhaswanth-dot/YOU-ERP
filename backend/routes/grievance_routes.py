from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from database import get_supabase
from auth import get_current_user, TokenData
from datetime import datetime, timezone
import uuid

router = APIRouter()

class GrievanceCreate(BaseModel):
    citizen_name: Optional[str] = "Anonymous"
    citizen_phone: Optional[str] = None
    location: Optional[str] = None
    village: Optional[str] = None  # Legacy field
    category: Optional[str] = "Miscellaneous"
    description: str
    issue_type: Optional[str] = "Other"  # Legacy field
    priority_level: Optional[str] = "MEDIUM"
    ai_priority: Optional[int] = 5
    deadline_timestamp: Optional[str] = None

class GrievanceUpdate(BaseModel):
    status: Optional[str] = None
    resolution_notes: Optional[str] = None
    assigned_to: Optional[str] = None
    priority_level: Optional[str] = None

@router.post("/")
async def create_grievance(
    data: GrievanceCreate,
    current_user: TokenData = Depends(get_current_user)
):
    if not current_user.politician_id:
        raise HTTPException(status_code=403, detail="User not associated with a politician")
    
    supabase = get_supabase()
    grievance_id = str(uuid.uuid4())
    
    # Use location or village for backward compatibility
    location_value = data.location or data.village or "Unknown"
    # Use category or issue_type for backward compatibility
    category_value = data.category or data.issue_type or "Miscellaneous"
    
    grievance_data = {
        'id': grievance_id,
        'politician_id': current_user.politician_id,
        'citizen_name': data.citizen_name or "Anonymous",
        'citizen_phone': data.citizen_phone,
        'village': location_value,
        'category': category_value,
        'description': data.description,
        'issue_type': category_value,
        'ai_priority': data.ai_priority,
        'priority_level': data.priority_level,
        'status': 'PENDING',
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    result = supabase.table('grievances').insert(grievance_data).execute()
    return {"message": "Grievance created successfully", "id": grievance_id}

@router.get("/")
async def get_grievances(
    status: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user)
):
    if not current_user.politician_id:
        raise HTTPException(status_code=403, detail="User not associated with a politician")
    
    supabase = get_supabase()
    query = supabase.table('grievances').select('*').eq('politician_id', current_user.politician_id)
    
    if status:
        query = query.eq('status', status)
    
    result = query.order('created_at', desc=True).execute()
    return result.data

@router.get("/metrics")
async def get_grievance_metrics(current_user: TokenData = Depends(get_current_user)):
    """
    Get comprehensive metrics for grievances including resolved, unresolved, and long pending
    """
    if not current_user.politician_id:
        raise HTTPException(status_code=403, detail="User not associated with a politician")
    
    supabase = get_supabase()
    all_grievances = supabase.table('grievances').select('*').eq('politician_id', current_user.politician_id).execute()
    
    total = len(all_grievances.data)
    
    # Count by status
    resolved = len([g for g in all_grievances.data if g.get('status', '').upper() == 'RESOLVED'])
    in_progress = len([g for g in all_grievances.data if g.get('status', '').upper() == 'IN_PROGRESS'])
    pending = len([g for g in all_grievances.data if g.get('status', '').upper() == 'PENDING'])
    
    # Calculate unresolved (pending + in_progress)
    unresolved = pending + in_progress
    
    # Calculate long pending (pending for more than 7 days)
    long_pending_days = 7
    now = datetime.now(timezone.utc)
    long_pending_count = 0
    
    for g in all_grievances.data:
        if g.get('status', '').upper() in ['PENDING', 'IN_PROGRESS']:
            created_at = datetime.fromisoformat(g['created_at'].replace('Z', '+00:00'))
            days_elapsed = (now - created_at).days
            if days_elapsed >= long_pending_days:
                long_pending_count += 1
    
    # Calculate resolution rate
    resolution_rate = round((resolved / total * 100) if total > 0 else 0, 1)
    
    # Calculate average resolution time (for resolved issues)
    resolved_issues = [g for g in all_grievances.data if g.get('status', '').upper() == 'RESOLVED' and g.get('resolved_at')]
    avg_resolution_days = 0
    
    if resolved_issues:
        total_days = 0
        for g in resolved_issues:
            created = datetime.fromisoformat(g['created_at'].replace('Z', '+00:00'))
            resolved_at = datetime.fromisoformat(g['resolved_at'].replace('Z', '+00:00'))
            total_days += (resolved_at - created).days
        avg_resolution_days = round(total_days / len(resolved_issues), 1)
    
    return {
        "total": total,
        "resolved": resolved,
        "unresolved": unresolved,
        "pending": pending,
        "in_progress": in_progress,
        "long_pending": long_pending_count,
        "long_pending_days": long_pending_days,
        "resolution_rate": resolution_rate,
        "avg_resolution_days": avg_resolution_days
    }

@router.get("/{grievance_id}")
async def get_grievance(
    grievance_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    supabase = get_supabase()
    result = supabase.table('grievances').select('*').eq('id', grievance_id).eq('politician_id', current_user.politician_id).execute()
    
    if not result.data:
        raise HTTPException(status_code=404, detail="Grievance not found")
    
    return result.data[0]

@router.patch("/{grievance_id}")
async def update_grievance(
    grievance_id: str,
    data: GrievanceUpdate,
    current_user: TokenData = Depends(get_current_user)
):
    supabase = get_supabase()
    
    existing = supabase.table('grievances').select('*').eq('id', grievance_id).eq('politician_id', current_user.politician_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Grievance not found")
    
    update_data = {}
    if data.status:
        update_data['status'] = data.status.upper()
        if data.status.upper() == 'RESOLVED':
            update_data['resolved_at'] = datetime.now(timezone.utc).isoformat()
    if data.resolution_notes:
        update_data['resolution_notes'] = data.resolution_notes
    if data.assigned_to:
        update_data['assigned_to'] = data.assigned_to
    
    result = supabase.table('grievances').update(update_data).eq('id', grievance_id).execute()
    return {"message": "Grievance updated successfully"}

@router.get("/stats/overview")
async def get_grievance_stats(current_user: TokenData = Depends(get_current_user)):
    if not current_user.politician_id:
        raise HTTPException(status_code=403, detail="User not associated with a politician")
    
    supabase = get_supabase()
    all_grievances = supabase.table('grievances').select('status').eq('politician_id', current_user.politician_id).execute()
    
    total = len(all_grievances.data)
    pending = len([g for g in all_grievances.data if g.get('status', '').upper() == 'PENDING'])
    in_progress = len([g for g in all_grievances.data if g.get('status', '').upper() == 'IN_PROGRESS'])
    resolved = len([g for g in all_grievances.data if g.get('status', '').upper() == 'RESOLVED'])
    
    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved
    }


class AssignmentRequest(BaseModel):
    status: str = "assigned"
    assigned_official_phone: str

@router.put("/{grievance_id}/assign")
async def assign_grievance(
    grievance_id: str,
    data: AssignmentRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Feature B: Deep Link Assignment - Update ticket status and record assignee phone
    """
    supabase = get_supabase()
    
    existing = supabase.table('grievances').select('*').eq('id', grievance_id).eq('politician_id', current_user.politician_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Grievance not found")
    
    # Use actual column name from schema
    update_data = {
        'status': data.status.upper(),
        'assigned_official_phone': data.assigned_official_phone
    }
    
    result = supabase.table('grievances').update(update_data).eq('id', grievance_id).execute()
    return {"message": "Grievance assigned successfully", "assignee": data.assigned_official_phone}


# ==============================================================================
# 10-STEP WORKFLOW: Resolution Endpoints
# ==============================================================================

class StartWorkRequest(BaseModel):
    notes: Optional[str] = None

@router.put("/{grievance_id}/start-work")
async def start_work(
    grievance_id: str,
    data: StartWorkRequest = None,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Step 8: OSD/PA clicks 'Start Work' - Updates status to IN_PROGRESS
    """
    supabase = get_supabase()
    
    existing = supabase.table('grievances').select('*').eq('id', grievance_id).eq('politician_id', current_user.politician_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Grievance not found")
    
    update_data = {
        'status': 'IN_PROGRESS'
    }
    
    supabase.table('grievances').update(update_data).eq('id', grievance_id).execute()
    
    return {"message": "Work started on grievance", "status": "IN_PROGRESS"}


class UploadResolutionRequest(BaseModel):
    resolution_image_url: str
    notes: Optional[str] = None

@router.put("/{grievance_id}/upload-resolution-photo")
async def upload_resolution_photo(
    grievance_id: str,
    data: UploadResolutionRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Step 8: Upload photo verification before marking resolved
    """
    supabase = get_supabase()
    
    existing = supabase.table('grievances').select('*').eq('id', grievance_id).eq('politician_id', current_user.politician_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Grievance not found")
    
    update_data = {
        'resolution_image_url': data.resolution_image_url
    }
    
    supabase.table('grievances').update(update_data).eq('id', grievance_id).execute()
    
    return {"message": "Resolution photo uploaded", "can_resolve": True}


class ResolveRequest(BaseModel):
    send_notification: bool = True
    notes: Optional[str] = None

@router.put("/{grievance_id}/resolve")
async def resolve_grievance(
    grievance_id: str,
    data: ResolveRequest = None,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Step 8-9: Mark grievance as resolved (requires photo verification first)
    Optionally sends WhatsApp notification to citizen requesting feedback
    """
    supabase = get_supabase()
    
    existing = supabase.table('grievances').select('*').eq('id', grievance_id).eq('politician_id', current_user.politician_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Grievance not found")
    
    grievance = existing.data[0]
    
    # Check if resolution photo exists
    if not grievance.get('resolution_image_url'):
        raise HTTPException(status_code=400, detail="Photo verification required before resolving. Please upload a resolution photo first.")
    
    update_data = {
        'status': 'RESOLVED'
    }
    
    supabase.table('grievances').update(update_data).eq('id', grievance_id).execute()

    
    # Send WhatsApp notification if requested
    notification_sent = False
    if data and data.send_notification:
        citizen_phone = grievance.get('citizen_phone')
        if citizen_phone:
            try:
                import httpx
                backend_url = "http://localhost:8001"
                async with httpx.AsyncClient() as client:
                    await client.post(
                        f"{backend_url}/api/whatsapp/send-resolution",
                        params={"grievance_id": grievance_id},
                        timeout=10.0
                    )
                notification_sent = True
            except Exception as e:
                print(f"⚠️ Failed to send resolution notification: {e}")
    
    return {
        "message": "Grievance resolved successfully",
        "status": "RESOLVED",
        "notification_sent": notification_sent
    }


class FeedbackRequest(BaseModel):
    rating: int

@router.put("/{grievance_id}/feedback")
async def record_feedback(
    grievance_id: str,
    data: FeedbackRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Step 10: Record citizen feedback rating (1-5)
    """
    if data.rating < 1 or data.rating > 5:
        raise HTTPException(status_code=400, detail="Rating must be between 1 and 5")
    
    supabase = get_supabase()
    
    existing = supabase.table('grievances').select('*').eq('id', grievance_id).eq('politician_id', current_user.politician_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Grievance not found")
    
    supabase.table('grievances').update({
        'feedback_rating': data.rating
    }).eq('id', grievance_id).execute()
    
    return {"message": "Feedback recorded", "rating": data.rating}


# ==============================================================================
# FILE UPLOAD ENDPOINT
# ==============================================================================
from fastapi import UploadFile, File
import os
import httpx

SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
STORAGE_BUCKET = os.environ.get('STORAGE_BUCKET', 'Grievances')

@router.post("/{grievance_id}/upload-file")
async def upload_resolution_file(
    grievance_id: str,
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Upload resolution photo from device (not just URL)
    """
    supabase = get_supabase()
    
    existing = supabase.table('grievances').select('*').eq('id', grievance_id).eq('politician_id', current_user.politician_id).execute()
    if not existing.data:
        raise HTTPException(status_code=404, detail="Grievance not found")
    
    # Read file content
    content = await file.read()
    content_type = file.content_type or 'image/jpeg'
    
    # Generate unique filename
    import random
    import string
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
    extension = file.filename.split('.')[-1] if file.filename else 'jpg'
    file_name = f"resolution/{int(datetime.now().timestamp())}_{random_suffix}.{extension}"
    
    # Upload to Supabase Storage
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/{file_name}"
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        upload_response = await client.post(
            upload_url,
            headers={
                'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
                'Content-Type': content_type
            },
            content=content
        )
        
        if upload_response.status_code not in [200, 201]:
            raise HTTPException(status_code=500, detail=f"Upload failed: {upload_response.text}")
        
        # Generate signed URL
        sign_url = f"{SUPABASE_URL}/storage/v1/object/sign/{STORAGE_BUCKET}/{file_name}"
        sign_response = await client.post(
            sign_url,
            headers={
                'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
                'Content-Type': 'application/json'
            },
            json={"expiresIn": 604800}
        )
        
        if sign_response.status_code == 200:
            sign_data = sign_response.json()
            file_url = f"{SUPABASE_URL}/storage/v1{sign_data.get('signedURL', '')}"
        else:
            file_url = f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{file_name}"
    
    # Update grievance with resolution photo URL
    supabase.table('grievances').update({
        'resolution_image_url': file_url
    }).eq('id', grievance_id).execute()
    
    return {
        "message": "File uploaded successfully",
        "url": file_url,
        "can_resolve": True
    }