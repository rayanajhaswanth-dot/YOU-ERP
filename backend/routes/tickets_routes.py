from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime, timezone
from database import get_supabase
from auth import get_current_user, TokenData

router = APIRouter()

# Schema for creating a ticket
class TicketCreate(BaseModel):
    title: str
    description: str
    location: str = "Unknown"
    priority_level: str = "LOW"
    assigned_official_phone: str = None

# Schema for reading a ticket
class Ticket(BaseModel):
    id: str
    title: str
    description: str
    status: str
    created_at: str
    priority_level: str
    deadline_timestamp: Optional[str] = None

@router.get("/", response_model=List[Ticket])
async def get_tickets(user: TokenData = Depends(get_current_user)):
    """
    Fetch tickets. 
    Role Check: Leaders/OSD see all. Citizens see only theirs (handled by Supabase RLS).
    """
    try:
        supabase = get_supabase()
        response = supabase.table("grievances").select("*").order("created_at", desc=True).execute()
        
        # Map grievance fields to ticket format
        tickets = []
        for g in response.data:
            tickets.append({
                "id": g.get("id"),
                "title": g.get("issue_type", "General Issue"),
                "description": g.get("description", ""),
                "status": g.get("status", "PENDING"),
                "created_at": g.get("created_at", ""),
                "priority_level": g.get("priority_level", "LOW"),
                "deadline_timestamp": g.get("deadline_timestamp")
            })
        return tickets
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=Ticket)
async def create_ticket(ticket: TicketCreate, user: TokenData = Depends(get_current_user)):
    try:
        supabase = get_supabase()
        import uuid
        
        data = {
            "id": str(uuid.uuid4()),
            "politician_id": user.politician_id,
            "issue_type": ticket.title,
            "description": ticket.description,
            "village": ticket.location,
            "priority_level": ticket.priority_level,
            "status": "PENDING",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        
        response = supabase.table("grievances").insert(data).execute()
        if not response.data:
            raise HTTPException(status_code=400, detail="Failed to create ticket")
        
        created = response.data[0]
        return {
            "id": created["id"],
            "title": created.get("issue_type", ticket.title),
            "description": created["description"],
            "status": created["status"],
            "created_at": created["created_at"],
            "priority_level": created["priority_level"],
            "deadline_timestamp": created.get("deadline_timestamp")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{ticket_id}")
async def delete_ticket(ticket_id: str, user: TokenData = Depends(get_current_user)):
    """
    CTO UPDATE: RBAC Expansion.
    OSD, Registrar, AND Leader/Politician can delete tickets.
    """
    user_role = user.role.lower() if user.role else "citizen"
    
    # Updated allowed roles list
    allowed_roles = ["osd", "registrar", "leader", "politician"]
    
    if user_role not in allowed_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Access Denied: You do not have permission to delete records."
        )

    try:
        supabase = get_supabase()
        response = supabase.table("grievances").delete().eq("id", ticket_id).execute()
        return {"message": "Ticket deleted successfully", "id": ticket_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch("/{ticket_id}/assign")
async def assign_ticket(ticket_id: str, official_phone: str, user: TokenData = Depends(get_current_user)):
    """
    Assigns a ticket to an official.
    CTO UPDATE: Allowed for OSD, Registrar, Leader, Politician.
    """
    user_role = user.role.lower() if user.role else "citizen"
    
    allowed_roles = ["osd", "registrar", "leader", "politician"]
    
    if user_role not in allowed_roles:
        raise HTTPException(status_code=403, detail="Not authorized to assign tickets.")

    try:
        supabase = get_supabase()
        response = supabase.table("grievances").update({
            "assigned_to": official_phone,
            "status": "IN_PROGRESS"
        }).eq("id", ticket_id).execute()
        
        return {"message": "Ticket assigned successfully", "data": response.data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
