from fastapi import APIRouter, HTTPException, Request, Form
from pydantic import BaseModel
from typing import Optional
from database import get_supabase
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import uuid
import tempfile
import json
import base64
import httpx
import random
import string
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType

router = APIRouter()

# Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
SARVAM_API_KEY = os.environ.get('SARVAM_API_KEY')

# Supabase Storage Configuration
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
STORAGE_BUCKET = os.environ.get('STORAGE_BUCKET', 'Grievances')

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


# ============================================================
# HELPER: Download media from Twilio with redirect handling
# ============================================================
async def download_twilio_media(url: str, client: httpx.AsyncClient) -> dict:
    """
    Securely downloads media from Twilio.
    Handles Twilio -> S3 redirects properly.
    """
    if not url:
        return None
    
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    
    print(f"[STAGE: TWILIO_DOWNLOAD] Initiating download from: {url[:60]}...")
    print(f"[STAGE: TWILIO_DOWNLOAD] Using SID: {TWILIO_ACCOUNT_SID[:10]}...")
    
    # First request - may redirect to S3
    response = await client.get(url, auth=auth, follow_redirects=False)
    
    print(f"[STAGE: TWILIO_DOWNLOAD] Initial response: {response.status_code}")
    
    # Handle Twilio -> S3 Redirects
    if response.status_code >= 300 and response.status_code < 400:
        redirect_url = response.headers.get('location')
        print(f"[STAGE: TWILIO_DOWNLOAD] Following redirect to S3...")
        # Fetch from S3 WITHOUT Twilio auth headers
        response = await client.get(redirect_url)
        print(f"[STAGE: TWILIO_DOWNLOAD] S3 response: {response.status_code}")
    
    if response.status_code == 401:
        raise Exception("Twilio Auth Failed: Check TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN in .env")
    
    if response.status_code != 200:
        raise Exception(f"Twilio Download Failed: HTTP {response.status_code}")
    
    buffer = response.content
    
    if len(buffer) == 0:
        raise Exception("Downloaded buffer is empty")
    
    content_type = response.headers.get('content-type', 'application/octet-stream')
    
    # Check for XML error response
    if 'xml' in content_type.lower():
        text = buffer.decode('utf-8', errors='ignore')[:200]
        raise Exception(f"Twilio returned XML error: {text}")
    
    print(f"[STAGE: TWILIO_DOWNLOAD] SUCCESS - {len(buffer)} bytes, type: {content_type}")
    return {'buffer': buffer, 'content_type': content_type}


# ============================================================
# HELPER: Upload to Supabase Storage & Generate Signed URL
# ============================================================
async def upload_to_supabase_storage(file_obj: dict, folder: str, client: httpx.AsyncClient) -> str:
    """
    Uploads buffer to Supabase Storage via REST API.
    Returns a SIGNED URL (valid for 60 seconds) for private bucket compatibility.
    """
    # Generate unique filename
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
    extension = file_obj['content_type'].split('/')[-1].split(';')[0]
    if extension == 'mpeg':
        extension = 'mp3'
    elif extension == 'ogg':
        extension = 'ogg'
    
    file_name = f"{folder}/{int(datetime.now().timestamp())}_{random_suffix}.{extension}"
    
    # Step 1: Upload to Supabase Storage
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/{file_name}"
    
    print(f"[STAGE: SUPABASE_UPLOAD] Uploading to: {upload_url}")
    
    upload_response = await client.post(
        upload_url,
        headers={
            'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
            'Content-Type': file_obj['content_type']
        },
        content=file_obj['buffer'],
        timeout=60.0
    )
    
    if upload_response.status_code not in [200, 201]:
        error_text = upload_response.text
        print(f"[STAGE: SUPABASE_UPLOAD] ERROR: {error_text}")
        if "404" in error_text:
            raise Exception(f"Bucket '{STORAGE_BUCKET}' not found. Create it in Supabase Dashboard.")
        elif "401" in error_text or "403" in error_text:
            raise Exception("Check SUPABASE_SERVICE_KEY - unauthorized access.")
        raise Exception(f"Supabase Upload Failed: {error_text}")
    
    print(f"[STAGE: SUPABASE_UPLOAD] SUCCESS - File uploaded")
    
    # Step 2: Generate Signed URL (valid for 300 seconds = 5 mins)
    sign_url = f"{SUPABASE_URL}/storage/v1/object/sign/{STORAGE_BUCKET}/{file_name}"
    
    print(f"[STAGE: SIGNED_URL] Generating signed URL...")
    
    sign_response = await client.post(
        sign_url,
        headers={
            'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
            'Content-Type': 'application/json'
        },
        json={"expiresIn": 300},
        timeout=30.0
    )
    
    if sign_response.status_code == 200:
        sign_data = sign_response.json()
        signed_url = f"{SUPABASE_URL}/storage/v1{sign_data.get('signedURL', '')}"
        print(f"[STAGE: SIGNED_URL] SUCCESS: {signed_url[:80]}...")
        return signed_url
    else:
        # Fallback to public URL if signing fails
        public_url = f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{file_name}"
        print(f"[STAGE: SIGNED_URL] Fallback to public URL: {public_url}")
        return public_url


class WhatsAppMessage(BaseModel):
    to: str
    message: str

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """
    Twilio WhatsApp webhook endpoint
    Receives incoming messages from WhatsApp users (text and images)
    """
    try:
        form_data = await request.form()
        
        from_number = form_data.get('From', '')
        to_number = form_data.get('To', '')
        message_body = form_data.get('Body', '')
        message_sid = form_data.get('MessageSid', '')
        profile_name = form_data.get('ProfileName', 'Constituent')
        
        # Check for media (images)
        num_media = int(form_data.get('NumMedia', 0))
        media_url = None
        media_content_type = None
        
        if num_media > 0:
            media_url = form_data.get('MediaUrl0', '')
            media_content_type = form_data.get('MediaContentType0', '')
            print(f"📸 Received media: {media_content_type} from {from_number}")
        
        print(f"📱 Received WhatsApp message from {from_number}: {message_body}")
        print(f"   To: {to_number}, SID: {message_sid}, Profile: {profile_name}")
        print(f"   Media: {num_media} files, URL: {media_url}")
        
        phone_clean = from_number.replace('whatsapp:', '').strip()
        
        response_message = await process_whatsapp_message(
            phone_clean,
            message_body,
            profile_name,
            message_sid,
            media_url,
            media_content_type
        )
        
        print(f"📤 Sending response: {response_message[:100]}...")
        
        resp = MessagingResponse()
        resp.message(response_message)
        
        from fastapi.responses import Response
        return Response(content=str(resp), media_type="application/xml")
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        import traceback
        traceback.print_exc()
        
        resp = MessagingResponse()
        resp.message("Sorry, I encountered an error processing your message. Please try again.")
        
        from fastapi.responses import Response
        return Response(content=str(resp), media_type="application/xml")

async def process_whatsapp_message(
    phone: str,
    message: str,
    name: str,
    message_sid: str,
    media_url: str = None,
    media_content_type: str = None
) -> str:
    """
    Process incoming WhatsApp message with AI triage
    """
    try:
        supabase = get_supabase()
        
        if not media_url and message.lower() in ['hi', 'hello', 'hey', 'namaste']:
            return f"Namaste {name}! 🙏\n\nWelcome to YOU Governance ERP.\n\nI'm here to help you register grievances and get assistance.\n\nYou can:\n• Type your grievance\n• Send a voice message 🎤\n• Send a photo of the issue\n• Send a photo of a handwritten letter\n\nI'll analyze it with AI and register it immediately.\n\nCommands:\n• 'status' - Check your grievances\n• 'help' - Get help"
        
        if message.lower() == 'help':
            return "📋 How to use:\n\n1. Type your problem/grievance\n2. OR send a voice message 🎤 (Hindi, Tamil, Telugu, and more supported!)\n3. OR send a photo (handwritten letter, damaged infrastructure, etc.)\n4. I'll analyze it with AI and assign priority\n5. Our team will respond within 24-48 hours\n\n🎤 Voice messages in Indian languages will be automatically transcribed and translated!\n\nYou can check status anytime by typing 'status'"
        
        if message.lower() == 'status':
            grievances = supabase.table('grievances').select('*').order('created_at', desc=True).limit(3).execute()
            
            if not grievances.data:
                return "No recent grievances found.\n\nFeel free to share your concerns (text or photo) and I'll help register them."
            
            status_text = f"📊 Recent Grievances:\n\n"
            for idx, g in enumerate(grievances.data, 1):
                status_emoji = {'PENDING': '⏳', 'IN_PROGRESS': '🔄', 'RESOLVED': '✅'}.get(g.get('status', '').upper(), '📝')
                priority = g.get('ai_priority', 5)
                desc = g.get('description', 'No description')[:50]
                status_text += f"{idx}. {status_emoji} {g.get('status', 'PENDING')}\n   Priority: {priority}/10\n   {desc}...\n\n"
            
            return status_text
        
        # ============================================================
        # MULTIMODAL ORCHESTRATOR (V6) - Discrete Input Handling
        # Handles individual Image OCR or Voice Transcription
        # ============================================================
        
        extracted_text = ""
        image_description = ""
        voice_transcription = ""
        voice_transcript = None
        image_buffer = None
        
        # Determine media type
        is_image = False
        is_audio = False
        
        if media_url and media_content_type:
            if media_content_type.startswith('image/'):
                is_image = True
            elif media_content_type.startswith('audio/'):
                is_audio = True
            
            # URL extension fallback
            media_url_lower = media_url.lower()
            if any(ext in media_url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic']):
                is_image = True
                is_audio = False
            elif any(ext in media_url_lower for ext in ['.ogg', '.mp3', '.wav', '.m4a', '.opus', '.amr']):
                is_audio = True
                is_image = False
        
        print(f"📊 Media detection: is_image={is_image}, is_audio={is_audio}, content_type={media_content_type}")
        
        # ============================================================
        # MULTIMODAL ORCHESTRATOR V12 - Self-Diagnostic Mode
        # Tracks currentStage for precise error diagnosis
        # ============================================================
        
        stored_image_url = None
        stored_audio_url = None
        current_stage = "INITIALIZATION"
        
        if media_url and (is_audio or is_image):
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    current_stage = "TWILIO_DOWNLOAD"
                    # STEP 1: Download from Twilio with redirect handling
                    print(f"[STAGE: {current_stage}] Step 1: Downloading from Twilio...")
                    media_obj = await download_twilio_media(media_url, client)
                    
                    if not media_obj:
                        raise Exception("Failed to download media from Twilio")
                    
                    # STEP 2: Persist to Supabase Storage
                    current_stage = "SUPABASE_UPLOAD"
                    print(f"[STAGE: {current_stage}] Step 2: Persisting to Storage Bucket...")
                    try:
                        if is_audio:
                            stored_audio_url = await upload_to_supabase_storage(media_obj, 'audio', client)
                        elif is_image:
                            stored_image_url = await upload_to_supabase_storage(media_obj, 'images', client)
                    except Exception as storage_err:
                        print(f"⚠️ [STAGE: {current_stage}] Storage upload failed (continuing): {storage_err}")
                        # Continue processing even if storage fails
                    
                    # STEP 3: Process Audio via Sarvam (using buffer directly)
                    if is_audio:
                        current_stage = "SARVAM_AI_PROCESSING"
                        print(f"[STAGE: {current_stage}] Step 3: Sarvam Processing...")
                        try:
                            # Determine file type
                            content_type = media_obj['content_type']
                            if 'ogg' in content_type or 'opus' in content_type:
                                filename = 'input.ogg'
                                file_mime = 'audio/ogg'
                            elif 'mp3' in content_type or 'mpeg' in content_type:
                                filename = 'input.mp3'
                                file_mime = 'audio/mpeg'
                            else:
                                filename = 'input.ogg'
                                file_mime = 'audio/ogg'
                            
                            # Upload to Sarvam using buffer (most reliable)
                            files = {'file': (filename, media_obj['buffer'], file_mime)}
                            data = {'model': 'saaras:v1'}
                            
                            sarvam_response = await client.post(
                                "https://api.sarvam.ai/speech-to-text-translate",
                                headers={"api-subscription-key": SARVAM_API_KEY},
                                files=files,
                                data=data,
                                timeout=90.0
                            )
                            
                            if sarvam_response.status_code == 200:
                                sarvam_data = sarvam_response.json()
                                voice_transcript = sarvam_data.get("transcript") or sarvam_data.get("text", "")
                                language_code = sarvam_data.get("language_code", "unknown")
                                
                                lang_map = {
                                    "hi-IN": "Hindi", "ta-IN": "Tamil", "te-IN": "Telugu",
                                    "kn-IN": "Kannada", "ml-IN": "Malayalam", "bn-IN": "Bengali",
                                    "mr-IN": "Marathi", "gu-IN": "Gujarati", "pa-IN": "Punjabi",
                                    "en-IN": "English"
                                }
                                detected_lang = lang_map.get(language_code, language_code)
                                voice_transcription = f"[Voice in {detected_lang}] {voice_transcript}"
                                message = voice_transcript or message
                                print(f"✅ Sarvam transcribed ({detected_lang}): {voice_transcript[:100]}...")
                            else:
                                print(f"⚠️ Sarvam error: {sarvam_response.status_code}")
                        except Exception as sarvam_err:
                            print(f"⚠️ [STAGE: {current_stage}] Sarvam skipped: {sarvam_err}")
                    
                    # STEP 4: GPT-4o Analysis
                    current_stage = "GPT4o_ANALYSIS"
                    print(f"[STAGE: {current_stage}] Step 4: GPT-4o Analysis...")
                    
                    # Build GPT-4o messages
                    gpt_messages = [
                        {
                            "role": "system",
                            "content": "You are a Legislative Assistant for the 'YOU' Governance Platform. Extract grievance details into JSON."
                        },
                        {
                            "role": "user",
                            "content": []
                        }
                    ]
                    
                    # Build prompt based on available data
                    if is_image and voice_transcript:
                        prompt_text = f"TASK: Merge details from this letter image and voice transcript: \"{voice_transcript}\"."
                    elif is_image:
                        prompt_text = "TASK: OCR this physical letter or grievance image. Extract all text and identify the issue."
                    else:
                        prompt_text = f"TASK: Extract grievance details from voice transcript: \"{voice_transcript}\"."
                    
                    prompt_text += """
Return JSON: { 
    "constituent_name": "...", 
    "ward_number": "...", 
    "issue_summary": "...", 
    "extracted_text": "full OCR text if image",
    "ai_priority": 1-10, 
    "category": "Infrastructure/Water/Electricity/Roads/Sanitation/Other"
}"""
                    
                    gpt_messages[1]["content"].append({"type": "text", "text": prompt_text})
                    
                    # Add image URL for GPT-4o (use signed URL if available, else base64)
                    if is_image:
                        if stored_image_url:
                            # Use the signed storage URL (lighter payload, private bucket compatible)
                            print(f"[STAGE: {current_stage}] Using signed URL for GPT-4o")
                            gpt_messages[1]["content"].append({
                                "type": "image_url",
                                "image_url": {"url": stored_image_url, "detail": "high"}
                            })
                        else:
                            # Fallback to base64
                            print(f"[STAGE: {current_stage}] Using base64 fallback for GPT-4o")
                            image_base64 = base64.b64encode(media_obj['buffer']).decode('utf-8')
                            data_url = f"data:{media_obj['content_type']};base64,{image_base64}"
                            gpt_messages[1]["content"].append({
                                "type": "image_url",
                                "image_url": {"url": data_url, "detail": "high"}
                            })
                    
                    # Call GPT-4o Vision using emergentintegrations library
                    try:
                        from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContent
                        
                        vision_chat = LlmChat(
                            api_key=EMERGENT_LLM_KEY,
                            session_id=f"vision-{uuid.uuid4()}",
                            system_message="You are a Legislative Assistant for the 'YOU' Governance Platform. Extract grievance details from images and return valid JSON only."
                        ).with_model("openai", "gpt-4o")
                        
                        # Build prompt based on available data
                        if is_image and voice_transcript:
                            vision_prompt = f"TASK: Merge details from this letter image and voice transcript: \"{voice_transcript}\"."
                        elif is_image:
                            vision_prompt = "TASK: OCR this physical letter or grievance image. Extract all text and identify the issue."
                        else:
                            vision_prompt = f"TASK: Extract grievance details from voice transcript: \"{voice_transcript}\"."
                        
                        vision_prompt += """
Return JSON ONLY (no markdown, no code blocks): { 
    "constituent_name": "name if found, else 'Anonymous Citizen'", 
    "ward_number": "ward/village if found, else 'Not specified'", 
    "issue_summary": "brief summary of the grievance", 
    "extracted_text": "full OCR text if image",
    "ai_priority": 1-10 based on urgency, 
    "category": "Infrastructure/Water/Electricity/Roads/Sanitation/Other"
}"""
                        
                        # Create message with image if available
                        if is_image and media_obj:
                            # Encode image as base64
                            image_base64 = base64.b64encode(media_obj['buffer']).decode('utf-8')
                            
                            # IMPORTANT: Use content_type="image" (not mime type) for the library to handle images correctly
                            print(f"[STAGE: {current_stage}] Using FileContent with content_type='image' ({len(image_base64)} chars)")
                            
                            vision_message = UserMessage(
                                text=vision_prompt,
                                file_contents=[
                                    FileContent(
                                        content_type="image",  # Must be "image" not "image/jpeg"
                                        file_content_base64=image_base64
                                    )
                                ]
                            )
                        else:
                            vision_message = UserMessage(text=vision_prompt)
                        
                        print(f"[STAGE: {current_stage}] Calling GPT-4o via emergentintegrations...")
                        result_text = await vision_chat.send_message(vision_message)
                        print(f"📸 GPT-4o raw response: {result_text[:300]}...")
                        
                        try:
                            grievance_json = json.loads(result_text.replace('```json', '').replace('```', '').strip())
                            extracted_text = grievance_json.get("extracted_text", "")
                            image_description = grievance_json.get("issue_summary", "")
                            message = image_description or extracted_text[:200] or voice_transcript or message
                            
                            # Store media URL with grievance
                            if stored_image_url:
                                extracted_text = json.dumps({**grievance_json, "media_url": stored_image_url})
                            elif stored_audio_url:
                                extracted_text = json.dumps({**grievance_json, "media_url": stored_audio_url})
                            
                            print(f"✅ GPT-4o result: {message[:100]}...")
                        except json.JSONDecodeError as je:
                            print(f"⚠️ JSON parse error: {je}")
                            message = result_text[:200] if result_text else (voice_transcript or message)
                            
                    except Exception as vision_err:
                        print(f"❌ [STAGE: {current_stage}] GPT-4o Vision error: {vision_err}")
                        import traceback
                        traceback.print_exc()
                        # If we have voice transcript, use that as the message
                        if voice_transcript:
                            message = voice_transcript
                        
            except Exception as e:
                error_msg = str(e)
                print(f"❌ [STAGE: {current_stage}] Media processing error: {error_msg}")
                import traceback
                traceback.print_exc()
                
                # Self-diagnostic suggestions based on failure stage
                suggestion = ""
                if current_stage == "TWILIO_DOWNLOAD":
                    if "401" in error_msg or "Auth" in error_msg:
                        suggestion = "\n\n🔧 DIAGNOSIS: Twilio credentials may be incorrect. Please verify TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN."
                    else:
                        suggestion = "\n\n🔧 DIAGNOSIS: Could not download media from Twilio. The media URL may have expired."
                elif current_stage == "SUPABASE_UPLOAD":
                    if "404" in error_msg:
                        suggestion = "\n\n🔧 DIAGNOSIS: Storage bucket 'Grievances' may not exist in Supabase."
                    elif "401" in error_msg or "403" in error_msg:
                        suggestion = "\n\n🔧 DIAGNOSIS: Supabase service key may be incorrect."
                elif current_stage == "SARVAM_AI_PROCESSING":
                    suggestion = "\n\n🔧 DIAGNOSIS: Sarvam AI transcription failed. Check SARVAM_API_KEY."
                elif current_stage == "GPT4o_ANALYSIS":
                    suggestion = "\n\n🔧 DIAGNOSIS: OpenAI/GPT-4o analysis failed. Check API credits or key."
                
                if is_audio:
                    return f"🎤 I received your voice message but encountered an error processing it. Please try:\n• Recording again with clear audio\n• Speaking closer to the microphone\n• Or typing your grievance instead{suggestion}"
                else:
                    return f"📸 I received your image but encountered an error processing it. Please try:\n• Sending a clearer image\n• Or describing the issue in text{suggestion}"
        
        # If still no message after media processing
        if not message or message.strip() == "":
            return "I didn't receive any text or couldn't extract information from your media. Please try:\n• Typing your grievance\n• Sending a clearer photo\n• Describing the issue in text"
        
        # ============================================================
        # INTELLIGENT QUERY DETECTION & RESPONSE
        # Determines if message is a query or a grievance
        # ============================================================
        
        print("🤖 Analyzing message intent with AI...")
        
        intent = "GRIEVANCE"  # Default to grievance
        ai_response_text = ""
        priority = 5
        category = "Other"
        summary = message[:100]
        
        try:
            # Use emergentintegrations for intent detection
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"intent-{phone}-{uuid.uuid4()}",
                system_message="You are an intelligent assistant for a legislator's office. Analyze messages and determine if they are queries or grievances."
            ).with_model("gemini", "gemini-2.0-flash")
            
            intent_prompt = f"""Analyze this message from a citizen contacting a legislator's office:

MESSAGE: "{message}"

Determine the intent:
1. QUERY - If they're asking a question, seeking information, or making an inquiry (e.g., "What documents do I need?", "How do I apply for...?", "What is the process for...?")
2. GRIEVANCE - If they're reporting a problem, complaint, or issue that needs action (e.g., "No water supply", "Road is damaged", "Electricity problem")
3. GREETING - If they're just saying hello or making casual conversation
4. FOLLOWUP - If they're asking about status of an existing issue (e.g., "What happened to my complaint?")
5. THANKS - If they're expressing gratitude

If it's a QUERY, provide a helpful response answering their question.

Respond with JSON only (no markdown):
{{"intent": "QUERY|GRIEVANCE|GREETING|FOLLOWUP|THANKS", "confidence": 0.0-1.0, "response": "helpful response if QUERY/GREETING/FOLLOWUP/THANKS, empty if GRIEVANCE", "priority": 1-10, "category": "Infrastructure/Water/Electricity/Roads/Healthcare/Education/Sanitation/Other", "summary": "brief summary"}}"""
            
            user_msg = UserMessage(text=intent_prompt)
            ai_result = await chat.send_message(user_msg)
            
            print(f"🔍 AI Intent Result: {ai_result[:300]}")
            
            # Parse the response
            try:
                # Clean up the response
                clean_result = ai_result.replace('```json', '').replace('```', '').strip()
                analysis = json.loads(clean_result)
                
                intent = analysis.get("intent", "GRIEVANCE").upper()
                confidence = float(analysis.get("confidence", 0.5))
                ai_response_text = analysis.get("response", "")
                priority = int(analysis.get("priority", 5))
                category = analysis.get("category", "Other")
                summary = analysis.get("summary", message[:100])
                
                print(f"🎯 Detected intent: {intent} (confidence: {confidence})")
                
                # Handle non-grievance intents
                if intent == "QUERY" and confidence > 0.5:
                    response_text = ai_response_text if ai_response_text else "I understand you have a question. Let me help you with that."
                    return f"📝 {response_text}\n\n💡 If you have a specific complaint or issue that needs action, please describe it and I'll register it as a grievance."
                
                elif intent == "GREETING":
                    return f"Namaste {name}! 🙏\n\n{ai_response_text if ai_response_text else 'Welcome to the Governance Helpline!'}\n\nHow can I help you today?\n• Report a problem or grievance\n• Send a photo of an issue\n• Record a voice message 🎤\n• Type 'status' to check your grievances"
                
                elif intent == "FOLLOWUP":
                    # Get their recent grievances
                    recent = supabase.table('grievances').select('*').ilike('village', f'%{phone}%').order('created_at', desc=True).limit(3).execute()
                    
                    if recent.data:
                        status_text = f"📊 Your Recent Grievances:\n\n"
                        for idx, g in enumerate(recent.data, 1):
                            status_emoji = {'PENDING': '⏳', 'IN_PROGRESS': '🔄', 'RESOLVED': '✅'}.get(g.get('status', '').upper(), '📝')
                            p = g.get('ai_priority', 5)
                            desc = g.get('description', 'No description')[:60]
                            created = g.get('created_at', '')[:10]
                            status_text += f"{idx}. {status_emoji} {g.get('status', 'PENDING')}\n   📅 {created}\n   ⚡ Priority: {p}/10\n   📝 {desc}...\n\n"
                        return status_text + "💬 Need to add more details or have a new issue? Just type it."
                    else:
                        return f"I don't see any recent grievances from your number.\n\nWould you like to register a new complaint? Just describe your issue and I'll help you."
                
                elif intent == "THANKS":
                    return f"🙏 You're welcome, {name}!\n\n{ai_response_text if ai_response_text else 'Happy to help!'}\n\nIs there anything else I can assist you with?"
                    
            except json.JSONDecodeError as je:
                print(f"⚠️ JSON parse error: {je}")
                # Continue with grievance registration
                
        except Exception as e:
            print(f"⚠️ Intent detection error: {e}")
            # Continue with grievance registration as fallback
        
        # ============================================================
        # GRIEVANCE REGISTRATION (if not handled above)
        # ============================================================
        
        print(f"📝 Registering grievance - Category: {category}, Priority: {priority}")
        
        politicians = supabase.table('politicians').select('id').limit(1).execute()
        if not politicians.data:
            return "Sorry, system configuration error. Please contact support."
        
        politician_id = politicians.data[0]['id']
        
        grievance_id = str(uuid.uuid4())
        grievance_data = {
            'id': grievance_id,
            'politician_id': politician_id,
            'issue_type': category,
            'village': f'From {name} ({phone})',
            'description': message,
            'ai_priority': priority,
            'status': 'PENDING',
            'created_at': datetime.now(timezone.utc).isoformat()
        }
        
        supabase.table('grievances').insert(grievance_data).execute()
        print(f"✅ Grievance created: {grievance_id}")
        
        priority_label = "HIGH" if priority >= 8 else "MEDIUM" if priority >= 5 else "LOW"
        
        # Build media notes based on what was received
        media_note = ""
        if voice_transcription:
            media_note = "\n🎤 Voice message transcribed"
        elif media_url and media_content_type and media_content_type.startswith('image/'):
            media_note = "\n📸 Image received and analyzed"
        
        ocr_note = ""
        if extracted_text and len(extracted_text) > 10:
            ocr_note = "\n\nExtracted Text:\n{}...".format(extracted_text[:150])
        elif voice_transcription and len(voice_transcription) > 10:
            ocr_note = "\n\nTranscribed:\n{}...".format(voice_transcription[:200])
        
        response = """✅ Grievance Registered Successfully!

📋 Summary: {}

📁 Category: {}
⚡ Priority: {} ({}/10)
🔖 Reference ID: {}{}{}

Your concern has been registered and will be reviewed by our team within 24-48 hours.

You'll receive updates as we work on resolving this.

🙏 Thank you for reaching out!""".format(summary, category, priority_label, priority, grievance_id[:8].upper(), media_note, ocr_note)
        
        return response
        
    except Exception as e:
        print(f"❌ Processing error: {e}")
        return "Sorry, I encountered an error while processing your message. Our team has been notified. Please try again in a few minutes."

@router.post("/send")
async def send_whatsapp_message(data: WhatsAppMessage):
    """
    Send WhatsApp message via Twilio API
    """
    try:
        to_number = data.to if data.to.startswith('whatsapp:') else f'whatsapp:{data.to}'
        
        message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=data.message,
            to=to_number
        )
        
        return {
            "success": True,
            "message_sid": message.sid,
            "status": message.status
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def whatsapp_status():
    """
    Check WhatsApp bot status
    """
    return {
        "status": "active",
        "twilio_configured": bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN),
        "whatsapp_number": TWILIO_WHATSAPP_NUMBER
    }

@router.post("/broadcast")
async def broadcast_message(message: str, politician_id: str):
    """
    Broadcast message to all constituents of a politician
    """
    try:
        supabase = get_supabase()
        
        grievances = supabase.table('grievances').select('phone, constituent_name').eq('politician_id', politician_id).execute()
        
        unique_phones = list(set([g['phone'] for g in grievances.data if g['phone']]))
        
        sent_count = 0
        failed_count = 0
        
        for phone in unique_phones:
            try:
                to_number = f'whatsapp:{phone}' if not phone.startswith('whatsapp:') else phone
                
                twilio_client.messages.create(
                    from_=TWILIO_WHATSAPP_NUMBER,
                    body=message,
                    to=to_number
                )
                sent_count += 1
            except Exception as e:
                print(f"Failed to send to {phone}: {e}")
                failed_count += 1
        
        return {
            "success": True,
            "sent": sent_count,
            "failed": failed_count,
            "total": len(unique_phones)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))