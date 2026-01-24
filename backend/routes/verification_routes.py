from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from database import get_supabase
from auth import get_current_user, TokenData
import os
import base64
from emergentintegrations.llm.chat import LlmChat, UserMessage
import httpx
from datetime import datetime, timezone

router = APIRouter()

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

class VerificationResult(BaseModel):
    is_verified: bool
    confidence_score: float
    analysis: str
    recommendation: str

class ResolutionPhotoRequest(BaseModel):
    grievance_id: str
    image_base64: str
    notes: Optional[str] = None

@router.post("/verify-resolution")
async def verify_resolution(
    data: ResolutionPhotoRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Verify grievance resolution using before/after photo comparison
    Staff uploads 'after' photo, AI compares with 'before' photo
    """
    try:
        supabase = get_supabase()
        
        # Get grievance with original photo
        grievance = supabase.table('grievances').select('*').eq('id', data.grievance_id).eq('politician_id', current_user.politician_id).execute()
        
        if not grievance.data:
            raise HTTPException(status_code=404, detail="Grievance not found")
        
        grievance_data = grievance.data[0]
        
        # Check if grievance has original photo
        original_media_url = grievance_data.get('media_url')
        
        if not original_media_url:
            # No before photo, just verify the after photo describes resolution
            result = await verify_single_photo(
                data.image_base64,
                grievance_data.get('description', ''),
                grievance_data.get('issue_type', 'Other')
            )
        else:
            # Download original photo and compare
            result = await verify_before_after(
                original_media_url,
                data.image_base64,
                grievance_data.get('description', ''),
                grievance_data.get('issue_type', 'Other')
            )
        
        # Update grievance with resolution photo and verification
        update_data = {
            'resolution_media_url': f"data:image/jpeg;base64,{data.image_base64[:100]}...",  # Store reference
            'verification_status': 'verified' if result['is_verified'] else 'flagged',
            'verification_confidence': result['confidence_score'],
            'verification_notes': result['analysis'],
            'resolution_notes': data.notes or result['recommendation']
        }
        
        # Auto-approve if verified with high confidence
        if result['is_verified'] and result['confidence_score'] >= 0.8:
            update_data['status'] = 'RESOLVED'
            update_data['resolved_at'] = datetime.now(timezone.utc).isoformat()
            update_data['verified_by'] = current_user.user_id
        elif result['is_verified'] and result['confidence_score'] >= 0.6:
            update_data['status'] = 'RESOLVED'
            update_data['resolved_at'] = datetime.now(timezone.utc).isoformat()
            update_data['verified_by'] = current_user.user_id
            update_data['requires_review'] = True  # Flag for supervisor review
        else:
            update_data['status'] = 'IN_PROGRESS'
            update_data['requires_review'] = True
        
        supabase.table('grievances').update(update_data).eq('id', data.grievance_id).execute()
        
        return {
            "success": True,
            "verification": result,
            "status": update_data['status'],
            "requires_review": update_data.get('requires_review', False),
            "message": "Resolution verified and auto-approved!" if result['is_verified'] and result['confidence_score'] >= 0.8
                      else "Resolution verified but flagged for review" if result['is_verified']
                      else "Resolution NOT verified - issue appears unresolved"
        }
        
    except Exception as e:
        print(f"❌ Verification error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def verify_single_photo(
    after_photo_base64: str,
    original_issue: str,
    issue_type: str
) -> dict:
    """
    Verify resolution photo when no before photo exists
    """
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id="verification-single",
            system_message="You are an AI verification expert analyzing resolution photos for government grievances."
        ).with_model("gemini", "gemini-3-flash-preview")
        
        prompt = f"""Analyze this 'AFTER' resolution photo for a grievance.

Original Issue: {original_issue}
Issue Type: {issue_type}

Verify if the issue appears to be resolved based on the photo.

Provide analysis in JSON format:
{{
  "is_verified": <true if issue appears fixed, false otherwise>,
  "confidence_score": <0.0 to 1.0, how confident are you>,
  "analysis": "<detailed description of what you see in the photo>",
  "recommendation": "<approve, review, or reject with reasoning>"
}}

Respond ONLY with valid JSON."""
        
        user_message = UserMessage(text=prompt, image_base64=after_photo_base64)
        response = await chat.send_message(user_message)
        
        import json
        result = json.loads(response.replace('```json', '').replace('```', '').strip())
        return result
        
    except Exception as e:
        print(f"❌ Single photo verification error: {e}")
        return {
            "is_verified": False,
            "confidence_score": 0.0,
            "analysis": f"Error during verification: {str(e)}",
            "recommendation": "manual_review"
        }

async def verify_before_after(
    before_url: str,
    after_photo_base64: str,
    original_issue: str,
    issue_type: str
) -> dict:
    """
    Compare before and after photos to verify resolution
    """
    try:
        # Download before photo
        from routes.whatsapp_routes import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN
        
        async with httpx.AsyncClient() as client:
            if 'twilio.com' in before_url:
                auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                response = await client.get(before_url, auth=auth, timeout=30.0)
            else:
                response = await client.get(before_url, timeout=30.0)
            before_image_data = response.content
        
        before_photo_base64 = base64.b64encode(before_image_data).decode('utf-8')
        
        # Use Gemini Vision for before/after comparison
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id="verification-comparison",
            system_message="You are an AI verification expert comparing before/after photos for government grievance resolution."
        ).with_model("gemini", "gemini-3-flash-preview")
        
        prompt = f"""Compare these BEFORE and AFTER photos for a grievance resolution.

Original Issue: {original_issue}
Issue Type: {issue_type}

First image: BEFORE (the problem)
Second image: AFTER (claimed resolution)

Analyze both images and verify if the issue has been genuinely resolved.

Provide analysis in JSON format:
{{
  "is_verified": <true if issue is clearly resolved, false otherwise>,
  "confidence_score": <0.0 to 1.0, how confident are you in this verification>,
  "analysis": "<detailed comparison - what changed, what's the same, quality of resolution>",
  "recommendation": "<'auto_approve' if excellent resolution with high confidence, 'approve_with_review' if good but needs check, 'reject' if not resolved>",
  "before_description": "<what you see in before photo>",
  "after_description": "<what you see in after photo>",
  "changes_observed": "<list of specific changes between photos>"
}}

Be strict: Only verify as resolved if there's clear visual evidence of improvement.

Respond ONLY with valid JSON."""
        
        # Send both images for comparison
        user_message = UserMessage(
            text=prompt,
            image_base64=before_photo_base64
        )
        response_before = await chat.send_message(user_message)
        
        # Now analyze after photo
        user_message_after = UserMessage(
            text="Now analyze the AFTER photo (second image) and provide the complete comparison:",
            image_base64=after_photo_base64
        )
        response = await chat.send_message(user_message_after)
        
        import json
        result = json.loads(response.replace('```json', '').replace('```', '').strip())
        return result
        
    except Exception as e:
        print(f"❌ Before/after verification error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "is_verified": False,
            "confidence_score": 0.0,
            "analysis": f"Error during comparison: {str(e)}",
            "recommendation": "manual_review",
            "before_description": "Error loading before photo",
            "after_description": "Could not complete comparison",
            "changes_observed": "Verification failed - manual review required"
        }

@router.get("/verification-status/{grievance_id}")
async def get_verification_status(
    grievance_id: str,
    current_user: TokenData = Depends(get_current_user)
):
    """
    Get verification status for a grievance
    """
    try:
        supabase = get_supabase()
        grievance = supabase.table('grievances').select('*').eq('id', grievance_id).eq('politician_id', current_user.politician_id).execute()
        
        if not grievance.data:
            raise HTTPException(status_code=404, detail="Grievance not found")
        
        data = grievance.data[0]
        
        return {
            "grievance_id": grievance_id,
            "status": data.get('status'),
            "verification_status": data.get('verification_status'),
            "verification_confidence": data.get('verification_confidence'),
            "verification_notes": data.get('verification_notes'),
            "requires_review": data.get('requires_review', False),
            "has_before_photo": bool(data.get('media_url')),
            "has_after_photo": bool(data.get('resolution_media_url')),
            "verified_by": data.get('verified_by'),
            "resolved_at": data.get('resolved_at')
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))