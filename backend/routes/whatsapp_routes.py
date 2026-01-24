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
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType

router = APIRouter()

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
SARVAM_API_KEY = os.environ.get('SARVAM_API_KEY')

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

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
        
        # STEP 1: Download media from Twilio (with extended timeout)
        if media_url and (is_audio or is_image):
            print(f"📥 Step 1: Downloading media from Twilio...")
            try:
                async with httpx.AsyncClient(timeout=120.0) as client:
                    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                    media_response = await client.get(media_url, auth=auth, follow_redirects=True)
                    
                    if media_response.status_code != 200:
                        raise Exception(f"Twilio HTTP {media_response.status_code}: {media_response.reason_phrase}")
                    
                    media_buffer = media_response.content
                    
                    if len(media_buffer) == 0:
                        raise Exception("Downloaded buffer is empty")
                    
                    print(f"📥 Downloaded {len(media_buffer)} bytes successfully")
                    
                    if is_audio:
                        # STEP 2: Process Voice via Sarvam AI
                        print(f"🎤 Step 2: Processing Voice via Sarvam AI (saaras:v1)...")
                        try:
                            # Determine file type
                            if 'ogg' in media_content_type or 'opus' in media_content_type:
                                filename = 'input.ogg'
                                file_mime = 'audio/ogg'
                            elif 'mp3' in media_content_type or 'mpeg' in media_content_type:
                                filename = 'input.mp3'
                                file_mime = 'audio/mpeg'
                            else:
                                filename = 'input.ogg'
                                file_mime = 'audio/ogg'
                            
                            # Upload to Sarvam using multipart form-data
                            files = {'file': (filename, media_buffer, file_mime)}
                            data = {'model': 'saaras:v1'}
                            
                            sarvam_response = await client.post(
                                "https://api.sarvam.ai/speech-to-text-translate",
                                headers={"api-subscription-key": SARVAM_API_KEY},
                                files=files,
                                data=data,
                                timeout=90.0  # Extended timeout for transcription
                            )
                            
                            print(f"🎤 Sarvam response: {sarvam_response.status_code}")
                            
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
                                print(f"✅ Sarvam transcribed ({detected_lang}): {voice_transcript[:100]}...")
                            else:
                                print(f"⚠️ Sarvam failed ({sarvam_response.status_code}): {sarvam_response.text[:200]}")
                                # Fallback will use Gemini below
                                
                        except Exception as sarvam_err:
                            print(f"⚠️ Sarvam processing error: {sarvam_err}")
                        
                        # STEP 3: Use Gemini for grievance extraction from voice
                        print(f"🤖 Step 3: Registering Voice Grievance via Gemini...")
                        
                        prompt_text = f"""TASK: You are a Legislative Assistant for the 'YOU' Governance Platform.
INPUT: A voice transcript: "{voice_transcript or 'Unable to transcribe'}"

REQUIREMENT: Extract the constituent details and core grievance issue.
Return ONLY a valid JSON object.

SCHEMA:
{{
  "constituent_name": "name if mentioned, else 'Anonymous Citizen'",
  "ward_number": "ward/village if mentioned, else 'Not specified'",
  "issue_summary": "brief summary of the grievance",
  "ai_priority": 1-10 based on urgency,
  "category": "Infrastructure/Water/Electricity/Roads/Sanitation/Other",
  "resolution_suggestion": "one sentence action for the OSD"
}}"""
                        
                        gemini_payload = {
                            "contents": [{"parts": [{"text": prompt_text}]}],
                            "generationConfig": {"responseMimeType": "application/json"}
                        }
                        
                        gemini_response = await client.post(
                            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={EMERGENT_LLM_KEY}",
                            json=gemini_payload,
                            timeout=60.0
                        )
                        
                        if gemini_response.status_code == 200:
                            gemini_data = gemini_response.json()
                            if gemini_data.get("candidates"):
                                result_text = gemini_data["candidates"][0]["content"]["parts"][0]["text"]
                                try:
                                    grievance_json = json.loads(result_text.replace('```json', '').replace('```', '').strip())
                                    message = grievance_json.get("issue_summary", voice_transcript or message)
                                    extracted_text = json.dumps(grievance_json)
                                    print(f"✅ Gemini extracted grievance: {message[:100]}...")
                                except:
                                    message = voice_transcript or message
                        else:
                            message = voice_transcript or message
                            
                    elif is_image:
                        # STEP 2: Process Image via Gemini Vision
                        print(f"📸 Step 2: Processing Image via Gemini Vision...")
                        image_buffer = media_buffer
                        
                        # Determine MIME type
                        if 'jpeg' in media_content_type or 'jpg' in media_content_type:
                            mime_type = 'image/jpeg'
                        elif 'png' in media_content_type:
                            mime_type = 'image/png'
                        else:
                            mime_type = 'image/jpeg'
                        
                        # Encode image as base64
                        image_base64 = base64.b64encode(image_buffer).decode('utf-8')
                        
                        prompt_text = """TASK: You are a Legislative Assistant for the 'YOU' Governance Platform.
INPUT: An image of a physical letter or grievance document.

REQUIREMENT: 
1. Extract ALL text from the image using OCR
2. Identify the constituent name, ward/village, and core issue
3. Return ONLY a valid JSON object

SCHEMA:
{
  "constituent_name": "name if found, else 'Anonymous Citizen'",
  "ward_number": "ward/village if found, else 'Not specified'",
  "extracted_text": "full OCR text from the image",
  "issue_summary": "brief summary of the grievance",
  "ai_priority": 1-10 based on urgency,
  "category": "Infrastructure/Water/Electricity/Roads/Sanitation/Other",
  "resolution_suggestion": "one sentence action for the OSD"
}"""
                        
                        gemini_payload = {
                            "contents": [{
                                "parts": [
                                    {"inlineData": {"mimeType": mime_type, "data": image_base64}},
                                    {"text": prompt_text}
                                ]
                            }],
                            "generationConfig": {"responseMimeType": "application/json"}
                        }
                        
                        print(f"📤 Sending image ({len(image_base64)} chars base64) to Gemini...")
                        
                        gemini_response = await client.post(
                            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={EMERGENT_LLM_KEY}",
                            json=gemini_payload,
                            timeout=90.0  # Extended timeout for image processing
                        )
                        
                        print(f"📸 Gemini response: {gemini_response.status_code}")
                        
                        if gemini_response.status_code == 200:
                            gemini_data = gemini_response.json()
                            
                            if gemini_data.get("error"):
                                raise Exception(f"Gemini Error: {gemini_data['error'].get('message', 'Unknown')}")
                            
                            if gemini_data.get("candidates"):
                                result_text = gemini_data["candidates"][0]["content"]["parts"][0]["text"]
                                try:
                                    grievance_json = json.loads(result_text.replace('```json', '').replace('```', '').strip())
                                    extracted_text = grievance_json.get("extracted_text", "")
                                    image_description = grievance_json.get("issue_summary", "")
                                    message = image_description or extracted_text[:200] or message
                                    print(f"✅ Gemini OCR result: {message[:100]}...")
                                except json.JSONDecodeError as je:
                                    print(f"⚠️ JSON parse error: {je}")
                                    message = result_text[:200] if result_text else message
                        else:
                            error_text = gemini_response.text[:500]
                            print(f"❌ Gemini API error: {error_text}")
                            return "📸 I received your image but encountered an error processing it. Please try:\n• Sending a clearer image\n• Or describing the issue in text"
                            
            except Exception as e:
                print(f"❌ Media processing error: {e}")
                import traceback
                traceback.print_exc()
                
                if is_audio:
                    return "🎤 I received your voice message but encountered an error processing it. Please try:\n• Recording again with clear audio\n• Speaking closer to the microphone\n• Or typing your grievance instead"
                else:
                    return "📸 I received your image but encountered an error processing it. Please try:\n• Sending a clearer image\n• Or describing the issue in text"
            try:
                # Download image from Twilio
                print(f"📥 Downloading image from Twilio...")
                async with httpx.AsyncClient() as client:
                    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                    response = await client.get(media_url, auth=auth, timeout=30.0)
                    image_data = response.content
                    print(f"📥 Downloaded {len(image_data)} bytes")
                
                # Determine file extension and MIME type
                if 'jpeg' in media_content_type or 'jpg' in media_content_type:
                    file_ext = '.jpg'
                    mime_type = 'image/jpeg'
                elif 'png' in media_content_type:
                    file_ext = '.png'
                    mime_type = 'image/png'
                elif 'webp' in media_content_type:
                    file_ext = '.webp'
                    mime_type = 'image/webp'
                elif 'gif' in media_content_type:
                    file_ext = '.gif'
                    mime_type = 'image/gif'
                else:
                    file_ext = '.jpg'  # Default to jpg
                    mime_type = 'image/jpeg'
                
                # Save to temp file
                temp_path = os.path.join(tempfile.gettempdir(), f"image_{uuid.uuid4()}{file_ext}")
                with open(temp_path, 'wb') as f:
                    f.write(image_data)
                print(f"📁 Saved image to: {temp_path} (mime: {mime_type})")
                
                try:
                    # Create FileContentWithMimeType for the image
                    image_content = FileContentWithMimeType(
                        file_path=temp_path,
                        mime_type=mime_type
                    )
                    
                    # Use Gemini for vision (FileContentWithMimeType only works with Gemini)
                    chat = LlmChat(
                        api_key=EMERGENT_LLM_KEY,
                        session_id=f"vision-{phone}-{uuid.uuid4()}",
                        system_message="You are an AI assistant analyzing images for Indian legislators. Extract any text (OCR) and describe what you see. Focus on identifying problems, complaints, or issues shown in the image."
                    ).with_model("gemini", "gemini-2.5-flash")
                    
                    vision_prompt = """Analyze this image sent by a constituent. Provide:

1. **Extracted Text** (OCR): If there's any handwritten or printed text, extract it completely
2. **Image Description**: Describe what you see (damaged roads, water issues, infrastructure problems, etc.)
3. **Issue Identified**: What problem or grievance is being reported?

If it's a handwritten letter, extract the full text.
If it's a photo of an issue (broken road, water leak, etc.), describe it clearly.

Respond in this format:
TEXT: [extracted text here, or "No text found"]
DESCRIPTION: [what you see in the image]
ISSUE: [the problem being reported]"""
                    
                    user_message = UserMessage(
                        text=vision_prompt,
                        file_contents=[image_content]
                    )
                    
                    print(f"📤 Sending to Gemini 2.5 Flash for analysis...")
                    vision_response = await chat.send_message(user_message)
                    print(f"👁️ Vision response: {vision_response[:200]}...")
                    
                    # Parse the vision response
                    if "TEXT:" in vision_response:
                        text_part = vision_response.split("TEXT:")[1].split("DESCRIPTION:")[0].strip()
                        extracted_text = text_part if "No text found" not in text_part else ""
                    
                    if "DESCRIPTION:" in vision_response:
                        desc_part = vision_response.split("DESCRIPTION:")[1].split("ISSUE:")[0].strip()
                        image_description = desc_part
                    
                    if "ISSUE:" in vision_response:
                        issue_part = vision_response.split("ISSUE:")[1].strip()
                        if issue_part and issue_part != "":
                            message = issue_part
                        elif image_description:
                            message = image_description
                    
                    # Combine extracted text with image description
                    if extracted_text and image_description:
                        message = f"{extracted_text}\n\n[Image shows: {image_description}]"
                    elif extracted_text:
                        message = extracted_text
                    elif image_description:
                        message = f"[Photo received] {image_description}"
                    
                    print(f"✅ Extracted from image: {message[:100]}...")
                    
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                
            except Exception as e:
                print(f"❌ Image processing error: {e}")
                import traceback
                traceback.print_exc()
                return "📸 I received your image but encountered an error processing it. Please try:\n• Sending the image again\n• Or describe the issue in text"
        
        # If still no message after image processing
        if not message or message.strip() == "":
            return "I didn't receive any text or couldn't extract information from your image. Please try:\n• Typing your grievance\n• Sending a clearer photo\n• Describing the issue in text"
        
        print("🤖 Analyzing message with Gemini AI...")
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"whatsapp-{phone}",
            system_message="You are an AI assistant helping analyze constituent grievances for Indian legislators. Provide priority scores (1-10) and categorization."
        ).with_model("gemini", "gemini-3-flash-preview")
        
        analysis_prompt = f"""Analyze this constituent grievance and provide a JSON response:

Grievance: {message}

Provide:
{{
  "priority": <number 1-10, where 10 is most urgent>,
  "category": "<Infrastructure/Healthcare/Education/Employment/Social Welfare/Other>",
  "summary": "<brief 1-line summary>"
}}

Respond ONLY with valid JSON, no markdown."""
        
        user_message = UserMessage(text=analysis_prompt)
        ai_response = await chat.send_message(user_message)
        
        print(f"🤖 AI Response: {ai_response}")
        
        priority = 5
        category = "Other"
        summary = message[:100]
        
        try:
            analysis = json.loads(ai_response.replace('```json', '').replace('```', '').strip())
            priority = analysis.get('priority', 5)
            category = analysis.get('category', 'Other')
            summary = analysis.get('summary', message[:100])
        except:
            print("⚠️ Could not parse AI response, using defaults")
        
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