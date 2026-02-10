"""
YOU - Governance ERP WhatsApp Bot
OSD PERSONA UPDATE: Conversational Intelligence + Native Language Resolution
Updated: 2026-02-06

The bot now acts like a professional Officer on Special Duty (OSD):
- Distinguishes between CHAT, GRIEVANCE, STATUS, FEEDBACK
- Responds in user's native language
- Does NOT register "Thank you" or greetings as grievances
- Sends resolution notifications in user's original language
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from typing import Optional, Dict, Any
from database import get_supabase
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import uuid
import json
import httpx
import random
import string
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi.responses import Response

# Import the OSD Brain
from routes.ai_routes import (
    analyze_incoming_message,
    translate_text,
    extract_grievance_from_media,
    transcribe_audio,
    detect_language,
    map_to_official_category,
    categorize_text,
    OFFICIAL_CATEGORIES
)

router = APIRouter()

# Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# ==============================================================================
# MEDIA DOWNLOAD HELPER
# ==============================================================================

async def download_twilio_media(url: str, client: httpx.AsyncClient) -> dict:
    """Download media from Twilio"""
    if not url:
        return None
    
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    for attempt in range(3):
        try:
            response = await client.get(url, auth=auth, follow_redirects=True, timeout=60.0)
            if response.status_code == 200 and len(response.content) > 0:
                content_type = response.headers.get('content-type', 'application/octet-stream')
                if 'xml' not in content_type.lower():
                    return {'buffer': response.content, 'content_type': content_type}
            await asyncio.sleep(2)
        except Exception as e:
            print(f"⚠️ Media download attempt {attempt+1} failed: {e}")
            await asyncio.sleep(2)
    
    return None


async def upload_to_storage(file_obj: dict, folder: str, client: httpx.AsyncClient) -> str:
    """Upload to Supabase storage"""
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
    extension = file_obj['content_type'].split('/')[-1].split(';')[0]
    if extension == 'mpeg': extension = 'mp3'
    
    file_name = f"{folder}/{int(datetime.now().timestamp())}_{random_suffix}.{extension}"
    upload_url = f"{SUPABASE_URL}/storage/v1/object/Grievances/{file_name}"
    
    await client.post(
        upload_url,
        headers={'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}', 'Content-Type': file_obj['content_type']},
        content=file_obj['buffer'],
        timeout=60.0
    )
    
    return f"{SUPABASE_URL}/storage/v1/object/public/Grievances/{file_name}"


# ==============================================================================
# MAIN WEBHOOK - THE OSD PERSONA
# ==============================================================================

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """
    Main WhatsApp webhook with OSD Persona Intelligence.
    
    Flow:
    1. Receive message
    2. Detect language
    3. Classify intent (CHAT/GRIEVANCE/STATUS/FEEDBACK)
    4. Respond appropriately - DO NOT register chats as grievances
    """
    try:
        form_data = await request.form()
        
        from_number = form_data.get('From', '').replace('whatsapp:', '').strip()
        message_body = form_data.get('Body', '').strip()
        profile_name = form_data.get('ProfileName', 'Citizen')
        
        num_media = int(form_data.get('NumMedia', 0))
        media_url = form_data.get('MediaUrl0', '') if num_media > 0 else None
        media_content_type = form_data.get('MediaContentType0', '') if num_media > 0 else None
        
        print(f"📱 WhatsApp from {from_number} ({profile_name}): {message_body[:100]}...")
        
        response_message = await process_osd_conversation(
            phone=from_number,
            message=message_body,
            name=profile_name,
            media_url=media_url,
            media_content_type=media_content_type
        )
        
        resp = MessagingResponse()
        resp.message(response_message)
        
        return Response(content=str(resp), media_type="application/xml")
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        import traceback
        traceback.print_exc()
        
        resp = MessagingResponse()
        resp.message("I apologize for the inconvenience. Please try again in a moment.")
        
        return Response(content=str(resp), media_type="application/xml")


async def process_osd_conversation(phone: str, message: str, name: str, media_url: str = None, media_content_type: str = None) -> str:
    """
    The OSD Brain - Intelligent Conversation Handler
    
    Key Logic:
    1. If CHAT (greetings, thanks, ok): Reply politely, DO NOT register
    2. If FEEDBACK (rating, praise): Thank them, log internally, DO NOT register new grievance
    3. If STATUS: Fetch and respond in native language
    4. If GRIEVANCE: Extract, register, confirm in native language
    """
    supabase = get_supabase()
    
    # ===========================================================================
    # STEP 1: HANDLE MEDIA (PDF/Image/Audio)
    # ===========================================================================
    media_extracted = None
    
    if media_url and media_content_type:
        async with httpx.AsyncClient(timeout=120.0) as client:
            media_obj = await download_twilio_media(media_url, client)
            
            if media_obj:
                is_audio = 'audio' in media_content_type.lower() or 'ogg' in media_url.lower()
                is_image = 'image' in media_content_type.lower()
                is_pdf = 'pdf' in media_content_type.lower()
                
                # Upload to storage
                try:
                    folder = 'audio' if is_audio else ('documents' if is_pdf else 'images')
                    stored_url = await upload_to_storage(media_obj, folder, client)
                except Exception as e:
                    print(f"⚠️ Storage upload failed: {e}")
                    stored_url = None
                
                if is_audio:
                    # Transcribe voice message with detailed logging
                    print(f"🎤 Processing voice message: {len(media_obj['buffer'])} bytes, type: {media_content_type}")
                    transcript = await transcribe_audio(media_obj['buffer'], media_content_type)
                    if transcript and len(transcript.strip()) > 0:
                        message = transcript
                        print(f"✅ Voice transcribed successfully: {transcript[:100]}...")
                    else:
                        print(f"❌ Voice transcription returned empty result")
                        # Return error in user's likely language (default to Hinglish for Indian users)
                        return "Maaf kijiye, aapka voice message samajh nahi aaya. Kripya dobara bhejein ya text mein likhein."
                
                elif is_image or is_pdf:
                    # Extract grievance from document
                    media_extracted = await extract_grievance_from_media(media_obj['buffer'], media_content_type)
                    
                    if media_extracted:
                        media_extracted['media_url'] = stored_url
                        print(f"📎 Extracted from media: {media_extracted}")
                    else:
                        return await get_osd_response("media_error", detect_language(message) or 'en')
    
    # ===========================================================================
    # STEP 2: OSD BRAIN - INTENT CLASSIFICATION
    # ===========================================================================
    
    # If we have media-extracted data, it's definitely a grievance
    if media_extracted and media_extracted.get('description'):
        return await register_grievance_osd(
            phone=phone,
            name=media_extracted.get('name') or name,
            area=media_extracted.get('area'),
            category=map_to_official_category(media_extracted.get('category', 'Miscellaneous')),
            description=media_extracted.get('description'),
            language=media_extracted.get('language', 'en'),
            media_url=media_extracted.get('media_url'),
            supabase=supabase
        )
    
    # For text messages - use the OSD Brain
    if message:
        ai_decision = await analyze_incoming_message(message, name, phone)
        
        intent = ai_decision.get('intent', 'CHAT')
        user_lang = ai_decision.get('detected_language', 'en')
        ai_reply = ai_decision.get('reply')
        grievance_data = ai_decision.get('grievance_data')
        
        print(f"🧠 OSD Brain Decision: intent={intent}, lang={user_lang}")
        
        # ---------------------------------------------------------------------
        # CHAT: Greetings, Thank you, OK, General conversation
        # ---------------------------------------------------------------------
        if intent == 'CHAT':
            # The AI has generated a polite response - just return it
            # DO NOT register anything
            return ai_reply or await get_osd_response("chat_default", user_lang)
        
        # ---------------------------------------------------------------------
        # GENERAL_QUERY: Government schemes, processes, eligibility questions
        # ---------------------------------------------------------------------
        if intent == 'GENERAL_QUERY':
            # The AI has generated a wise, informative response about schemes/governance
            # DO NOT register as grievance - just provide information
            return ai_reply or await get_osd_response("query_default", user_lang)
        
        # ---------------------------------------------------------------------
        # FEEDBACK: Rating (1-5), Praise, Complaint about service
        # ---------------------------------------------------------------------
        if intent == 'FEEDBACK':
            # Try to update the latest grievance with rating if it's a number
            rating = extract_rating(message)
            if rating:
                await update_latest_grievance_rating(phone, rating, supabase)
            
            # Return thank you response - DO NOT register new grievance
            return ai_reply or await get_osd_response("feedback_thanks", user_lang)
        
        # ---------------------------------------------------------------------
        # STATUS: User asking for complaint status
        # ---------------------------------------------------------------------
        if intent == 'STATUS':
            return await get_grievance_status_osd(phone, user_lang, supabase)
        
        # ---------------------------------------------------------------------
        # GRIEVANCE: Actual complaint to register
        # ---------------------------------------------------------------------
        if intent == 'GRIEVANCE' and grievance_data:
            return await register_grievance_osd(
                phone=phone,
                name=grievance_data.get('name') or name,
                area=grievance_data.get('area'),
                category=map_to_official_category(grievance_data.get('category', 'Miscellaneous')),
                description=grievance_data.get('description') or message,
                language=user_lang,
                media_url=None,
                supabase=supabase
            )
    
    # Fallback - ask for clarification
    return await get_osd_response("clarification", 'en')


# ==============================================================================
# GRIEVANCE REGISTRATION
# ==============================================================================

async def register_grievance_osd(phone: str, name: str, area: str, category: str, description: str, language: str, media_url: str, supabase) -> str:
    """Register grievance and respond in user's native language"""
    
    # Get politician ID
    politicians = supabase.table('politicians').select('id').limit(1).execute()
    if not politicians.data:
        return "System error. Please contact the office directly."
    
    politician_id = politicians.data[0]['id']
    
    # Determine priority
    _, priority_level, deadline_hours = categorize_text(description)
    
    now = datetime.now(timezone.utc)
    deadline = (now + timedelta(hours=deadline_hours)).isoformat()
    
    # Grievance record - ALL IN ENGLISH for DB
    grievance_data = {
        'id': str(uuid.uuid4()),
        'politician_id': politician_id,
        'citizen_name': name or "Citizen",
        'citizen_phone': phone,
        'village': area or "Not specified",
        'category': category,  # ENGLISH
        'issue_type': category,  # ENGLISH
        'description': description,  # ENGLISH (AI translates during extraction)
        'priority_level': priority_level,
        'deadline_timestamp': deadline,
        'status': 'PENDING',
        'raw_input_language': language,  # Store user's language for future notifications
        'media_url': media_url,
        'language_preference': language,
        'created_at': now.isoformat()
    }
    
    try:
        result = supabase.table('grievances').insert(grievance_data).execute()
        
        if result.data:
            ticket_id = str(result.data[0]['id'])[:8].upper()
            
            # Confirmation message in user's native language
            base_msg = f"I have noted your grievance and registered it with Ticket #{ticket_id}. I am forwarding this to the concerned department immediately. You will receive updates on WhatsApp."
            
            if language != 'en':
                response = await translate_text(base_msg, language)
            else:
                response = base_msg
            
            return f"✅ {response}"
            
    except Exception as e:
        print(f"❌ Registration error: {e}")
        import traceback
        traceback.print_exc()
    
    return "I apologize, there was an error registering your grievance. Please try again."


# ==============================================================================
# STATUS CHECK
# ==============================================================================

async def get_grievance_status_osd(phone: str, language: str, supabase) -> str:
    """Get grievance status in user's native language"""
    try:
        result = supabase.table('grievances').select('*').eq('citizen_phone', phone).order('created_at', desc=True).limit(5).execute()
        
        if not result.data:
            no_grievance_msg = "I could not find any grievances registered with your phone number."
            if language != 'en':
                return await translate_text(no_grievance_msg, language)
            return no_grievance_msg
        
        status_emojis = {'PENDING': '⏳', 'IN_PROGRESS': '🔄', 'RESOLVED': '✅', 'ASSIGNED': '👤'}
        
        header = "Here are your recent grievances:"
        if language != 'en':
            header = await translate_text(header, language)
        
        status_text = f"📊 {header}\n\n"
        
        for idx, g in enumerate(result.data, 1):
            status = (g.get('status') or 'PENDING').upper()
            emoji = status_emojis.get(status, '📝')
            created = g.get('created_at', '')[:10]
            category = g.get('category', 'Miscellaneous')
            ticket_id = str(g.get('id', ''))[:8].upper()
            
            status_text += f"{idx}. {emoji} #{ticket_id}\n"
            status_text += f"   📁 {category}\n"
            status_text += f"   📅 {created}\n"
            status_text += f"   Status: {status}\n\n"
        
        return status_text
        
    except Exception as e:
        print(f"❌ Status fetch error: {e}")
        return "Error fetching status. Please try again."


# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================

def extract_rating(text: str) -> int:
    """Extract rating (1-5) from text"""
    import re
    # Look for numbers 1-5
    match = re.search(r'\b([1-5])\b', text)
    if match:
        return int(match.group(1))
    
    # Check for words
    rating_words = {
        'excellent': 5, 'great': 5, 'amazing': 5, 'perfect': 5,
        'good': 4, 'satisfied': 4, 'happy': 4,
        'okay': 3, 'ok': 3, 'average': 3,
        'bad': 2, 'poor': 2, 'unsatisfied': 2,
        'terrible': 1, 'worst': 1, 'horrible': 1
    }
    
    text_lower = text.lower()
    for word, rating in rating_words.items():
        if word in text_lower:
            return rating
    
    return None


async def update_latest_grievance_rating(phone: str, rating: int, supabase):
    """Update the most recent resolved grievance with feedback rating"""
    try:
        result = supabase.table('grievances').select('id').eq('citizen_phone', phone).eq('status', 'RESOLVED').order('created_at', desc=True).limit(1).execute()
        
        if result.data:
            grievance_id = result.data[0]['id']
            supabase.table('grievances').update({'feedback_rating': rating}).eq('id', grievance_id).execute()
            print(f"✅ Updated rating to {rating} for grievance {grievance_id}")
    except Exception as e:
        print(f"⚠️ Could not update rating: {e}")


async def get_osd_response(response_type: str, language: str) -> str:
    """Get OSD-style response in user's language"""
    responses = {
        "chat_default": "I'm here to assist you. How may I help you today?",
        "query_default": "I'd be happy to help with information. Could you please specify which scheme or process you'd like to know about?",
        "feedback_thanks": "Thank you for your valuable feedback. We are committed to serving you better.",
        "voice_error": "I received your voice message but could not process it. Please try again or type your message.",
        "media_error": "I received your document but could not extract the information. Please describe your issue in text.",
        "clarification": "I'm here to help. Could you please provide more details about your concern?",
    }
    
    base_msg = responses.get(response_type, responses["chat_default"])
    
    if language != 'en':
        return await translate_text(base_msg, language)
    
    return base_msg


# ==============================================================================
# RESOLUTION NOTIFICATION (Called from grievance_routes when status = RESOLVED)
# ==============================================================================

async def send_resolution_notification(grievance_id: str, supabase) -> bool:
    """
    Send resolution notification to citizen in their NATIVE language.
    Called when OSD marks grievance as resolved.
    """
    try:
        result = supabase.table('grievances').select('*').eq('id', grievance_id).execute()
        
        if not result.data:
            return False
        
        grievance = result.data[0]
        citizen_phone = grievance.get('citizen_phone')
        user_lang = grievance.get('raw_input_language') or grievance.get('language_preference') or 'en'
        category = grievance.get('category', 'your issue')
        ticket_id = str(grievance_id)[:8].upper()
        
        if not citizen_phone:
            return False
        
        # Base English message
        base_msg = f"Dear Citizen, your grievance #{ticket_id} regarding '{category}' has been resolved. We hope you are satisfied with the action taken. Please reply with a rating (1-5) or your feedback."
        
        # Translate to user's native language
        if user_lang != 'en':
            final_msg = await translate_text(base_msg, user_lang)
        else:
            final_msg = base_msg
        
        final_msg = f"✅ {final_msg}"
        
        # Send via Twilio
        to_number = f'whatsapp:{citizen_phone}' if not citizen_phone.startswith('whatsapp:') else citizen_phone
        twilio_client.messages.create(from_=TWILIO_WHATSAPP_NUMBER, body=final_msg, to=to_number)
        
        print(f"📤 Resolution notification sent to {citizen_phone} in {user_lang}")
        return True
        
    except Exception as e:
        print(f"❌ Resolution notification error: {e}")
        import traceback
        traceback.print_exc()
        return False


# ==============================================================================
# API ENDPOINTS
# ==============================================================================

class WhatsAppMessage(BaseModel):
    to: str
    message: str

@router.post("/send")
async def send_whatsapp_message(data: WhatsAppMessage):
    """Send WhatsApp message"""
    try:
        to_number = data.to if data.to.startswith('whatsapp:') else f'whatsapp:{data.to}'
        message = twilio_client.messages.create(from_=TWILIO_WHATSAPP_NUMBER, body=data.message, to=to_number)
        return {"success": True, "message_sid": message.sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-resolution/{grievance_id}")
async def send_resolution_endpoint(grievance_id: str):
    """Send resolution notification to citizen in native language"""
    supabase = get_supabase()
    success = await send_resolution_notification(grievance_id, supabase)
    if success:
        return {"success": True, "message": "Resolution notification sent in citizen's native language"}
    raise HTTPException(status_code=500, detail="Failed to send notification")


@router.get("/status")
async def whatsapp_status():
    """Check WhatsApp bot status"""
    return {
        "status": "active",
        "version": "4.0 - Holistic Knowledge + Vision Analysis",
        "features": [
            "HOLISTIC KNOWLEDGE - AI retrieves official URLs for ANY scheme across ALL states",
            "IRON DOME System Prompt - Eliminates Token Overlap hallucinations",
            "Token Disambiguation: Tu/Mera/De/Se/Me → HINDI (not French/Spanish)",
            "JUGAAD Safety Net - Catches foreign language in final response",
            "VISION API - Image analysis for grievance photos using GPT-4o",
            "PDF Deep OCR - Extract grievance data from documents",
            "Intent Classification (CHAT/GRIEVANCE/STATUS/FEEDBACK/GENERAL_QUERY)",
            "Hinglish/Tenglish Support - Mirror exact user script",
            "Medical Domain: 108 Ambulance, Aarogyasri, PHC, CMO",
            "Voice Transcription: FFmpeg OGG→MP3 + Whisper",
            "Category Sanitization: Sadak/Pani → Infrastructure/Water",
            "Native Language Resolution Notifications"
        ],
        "intents": ["CHAT", "GRIEVANCE", "STATUS", "FEEDBACK", "GENERAL_QUERY"],
        "supported_languages": ["English", "Hinglish (Hindi-Roman)", "Tenglish (Telugu-Roman)", "Hindi (Devanagari)", "Telugu", "Tamil", "Kannada", "Malayalam", "Bengali"],
        "forbidden_languages": ["French", "Spanish", "German", "Portuguese"],
        "knowledge_coverage": [
            "All 28 States + 8 Union Territories",
            "All Central/National schemes",
            "Historical schemes (renamed/merged)",
            "Emergency services (108, 100, 112)"
        ],
        "categories": OFFICIAL_CATEGORIES
    }
