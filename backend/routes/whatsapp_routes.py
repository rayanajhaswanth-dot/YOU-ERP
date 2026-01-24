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
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType, ImageContent

router = APIRouter()

TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

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
        
        # Process image if present
        extracted_text = ""
        image_description = ""
        voice_transcription = ""
        
        # Determine media type - check both content-type and URL extension
        is_image = False
        is_audio = False
        
        if media_url and media_content_type:
            # Check content type first
            if media_content_type.startswith('image/'):
                is_image = True
            elif media_content_type.startswith('audio/'):
                is_audio = True
            
            # Also check URL extension as fallback (Twilio sometimes sends wrong content-type)
            media_url_lower = media_url.lower()
            if any(ext in media_url_lower for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.heic']):
                is_image = True
                is_audio = False
            elif any(ext in media_url_lower for ext in ['.ogg', '.mp3', '.wav', '.m4a', '.opus', '.amr']):
                is_audio = True
                is_image = False
        
        print(f"📊 Media detection: is_image={is_image}, is_audio={is_audio}, content_type={media_content_type}")
        
        # Check if it's an audio/voice message
        if media_url and is_audio:
            print(f"🎤 Processing voice message... Content-Type: {media_content_type}")
            try:
                import httpx
                
                # Download audio from Twilio
                print(f"📥 Downloading audio from: {media_url[:50]}...")
                async with httpx.AsyncClient() as client:
                    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                    response = await client.get(media_url, auth=auth, timeout=60.0)
                    audio_data = response.content
                    print(f"📥 Downloaded {len(audio_data)} bytes of audio")
                
                # Save to temp file for Gemini processing
                file_ext = '.ogg' if 'ogg' in media_content_type else '.mp3' if 'mp3' in media_content_type or 'mpeg' in media_content_type else '.wav'
                temp_path = os.path.join(tempfile.gettempdir(), f"voice_{uuid.uuid4()}{file_ext}")
                
                with open(temp_path, 'wb') as f:
                    f.write(audio_data)
                print(f"📁 Saved audio to: {temp_path}")
                
                try:
                    # Use Gemini 2.5 Flash for voice transcription (supports audio files)
                    chat = LlmChat(
                        api_key=EMERGENT_LLM_KEY,
                        session_id=f"voice-{phone}-{uuid.uuid4()}",
                        system_message="You are an expert audio transcription assistant specializing in Indian languages. You can accurately transcribe audio in Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, and other Indian regional languages."
                    ).with_model("gemini", "gemini-2.5-flash")
                    
                    # Create file content for audio
                    audio_file = FileContentWithMimeType(
                        file_path=temp_path,
                        mime_type=media_content_type
                    )
                    
                    transcription_prompt = """Listen to this voice message from a constituent. Transcribe it exactly as spoken.

If the audio is in a local Indian language (Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, or any other regional language):
1. Provide the original transcription
2. Provide an accurate English translation

Respond ONLY with a valid JSON object (no markdown, no code blocks):
{
    "original": "the exact transcription of what was spoken",
    "english_translation": "the English translation (same as original if already in English)",
    "language_detected": "the detected language"
}"""
                    
                    user_msg = UserMessage(
                        text=transcription_prompt,
                        file_contents=[audio_file]
                    )
                    
                    print(f"📤 Sending audio to Gemini 2.5 Flash for transcription...")
                    transcription_response = await chat.send_message(user_msg)
                    print(f"🎤 Voice transcription response: {transcription_response[:200]}...")
                    
                    # Parse the transcription response
                    try:
                        clean_response = transcription_response.strip()
                        if clean_response.startswith('```'):
                            clean_response = clean_response.split('\n', 1)[1]
                            if clean_response.endswith('```'):
                                clean_response = clean_response[:-3]
                            clean_response = clean_response.strip()
                        
                        transcription_data = json.loads(clean_response)
                        original_text = transcription_data.get("original", "")
                        english_text = transcription_data.get("english_translation", original_text)
                        detected_lang = transcription_data.get("language_detected", "Unknown")
                        
                        # Use English translation as the message for grievance processing
                        if detected_lang.lower() != "english" and english_text:
                            voice_transcription = f"[Voice message in {detected_lang}]\nOriginal: {original_text}\n\nEnglish: {english_text}"
                            message = english_text
                        else:
                            voice_transcription = f"[Voice message] {original_text}"
                            message = original_text
                        
                        print(f"✅ Voice transcribed: {message[:100]}...")
                        
                    except json.JSONDecodeError:
                        # If JSON parsing fails, use raw response
                        voice_transcription = f"[Voice message] {transcription_response}"
                        message = transcription_response
                        print(f"⚠️ Could not parse JSON, using raw response")
                    
                finally:
                    # Clean up temp file
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                        
            except Exception as e:
                print(f"❌ Voice processing error: {e}")
                import traceback
                traceback.print_exc()
                return "🎤 I received your voice message but encountered an error processing it. Please try:\n• Recording again with clear audio\n• Speaking closer to the microphone\n• Or typing your grievance instead"
        
        # Process image if present (existing logic)
        elif media_url and media_content_type and media_content_type.startswith('image/'):
            print(f"📸 Processing image with Gemini Vision... Content-Type: {media_content_type}")
            try:
                import httpx
                import base64
                
                # Download image from Twilio
                print(f"📥 Downloading image from: {media_url[:50]}...")
                async with httpx.AsyncClient() as client:
                    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
                    response = await client.get(media_url, auth=auth, timeout=30.0)
                    image_data = response.content
                    print(f"📥 Downloaded {len(image_data)} bytes")
                
                # Convert to base64 for Gemini
                image_base64 = base64.b64encode(image_data).decode('utf-8')
                print(f"📸 Converted to base64: {len(image_base64)} chars")
                
                # Create ImageContent object
                image_content = ImageContent(image_base64=image_base64)
                
                # Use GPT-4o for vision (more reliable)
                chat = LlmChat(
                    api_key=EMERGENT_LLM_KEY,
                    session_id=f"vision-{phone}-{uuid.uuid4()}",
                    system_message="You are an AI assistant analyzing images for Indian legislators. Extract any text (OCR) and describe what you see. Focus on identifying problems, complaints, or issues shown in the image."
                ).with_model("openai", "gpt-4o")
                
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
                
                print(f"📤 Sending to GPT-4o for analysis...")
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
                
            except Exception as e:
                print(f"❌ Image processing error: {e}")
                import traceback
                traceback.print_exc()
                return "I received your image but encountered an error processing it. Please try sending it again or describe the issue in text."
        
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
            import json
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