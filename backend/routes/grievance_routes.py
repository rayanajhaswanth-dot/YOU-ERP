from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List
from database import get_supabase
from auth import get_current_user, TokenData
from datetime import datetime, timezone
import uuid

router = APIRouter()

class GrievanceCreate(BaseModel):
    village: str
    description: str
    issue_type: str = "Other"
    ai_priority: Optional[int] = 5

class GrievanceUpdate(BaseModel):
    status: Optional[str] = None
    resolution_notes: Optional[str] = None
    assigned_to: Optional[str] = None

@router.post("/")
async def create_grievance(
    data: GrievanceCreate,
    current_user: TokenData = Depends(get_current_user)
):
    if not current_user.politician_id:
        raise HTTPException(status_code=403, detail="User not associated with a politician")
    
    supabase = get_supabase()
    grievance_id = str(uuid.uuid4())
    
    grievance_data = {
        'id': grievance_id,
        'politician_id': current_user.politician_id,
        'village': data.village,
        'description': data.description,
        'issue_type': data.issue_type,
        'ai_priority': data.ai_priority,
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
        update_data['status'] = data.status
        if data.status == 'resolved':
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
    pending = len([g for g in all_grievances.data if g['status'] == 'pending'])
    in_progress = len([g for g in all_grievances.data if g['status'] == 'in_progress'])
    resolved = len([g for g in all_grievances.data if g['status'] == 'resolved'])
    
    return {
        "total": total,
        "pending": pending,
        "in_progress": in_progress,
        "resolved": resolved
    }