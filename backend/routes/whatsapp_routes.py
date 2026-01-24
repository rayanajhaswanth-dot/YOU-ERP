from fastapi import APIRouter, HTTPException, Request, Form
from pydantic import BaseModel
from typing import Optional
from database import get_supabase
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import uuid
from datetime import datetime, timezone
from emergentintegrations.llm.chat import LlmChat, UserMessage

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
    Receives incoming messages from WhatsApp users
    """
    try:
        form_data = await request.form()
        
        from_number = form_data.get('From', '')
        to_number = form_data.get('To', '')
        message_body = form_data.get('Body', '')
        message_sid = form_data.get('MessageSid', '')
        profile_name = form_data.get('ProfileName', 'Constituent')
        
        print(f"📱 Received WhatsApp message from {from_number}: {message_body}")
        print(f"   To: {to_number}, SID: {message_sid}, Profile: {profile_name}")
        
        phone_clean = from_number.replace('whatsapp:', '').strip()
        
        response_message = await process_whatsapp_message(
            phone_clean,
            message_body,
            profile_name,
            message_sid
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
    message_sid: str
) -> str:
    """
    Process incoming WhatsApp message with AI triage
    """
    try:
        supabase = get_supabase()
        
        if message.lower() in ['hi', 'hello', 'hey', 'namaste']:
            return f"Namaste {name}! 🙏\n\nWelcome to YOU Governance ERP.\n\nI'm here to help you register grievances and get assistance.\n\nPlease describe your issue and I'll make sure it reaches the right people.\n\nCommands:\n• Type your grievance to register it\n• 'status' - Check your grievance status\n• 'help' - Get help"
        
        if message.lower() == 'help':
            return "📋 How to use:\n\n1. Simply type your problem/grievance\n2. I'll analyze it and assign priority\n3. Our team will respond within 24-48 hours\n\nYou can check status anytime by typing 'status'"
        
        if message.lower() == 'status':
            grievances = supabase.table('grievances').select('*').eq('phone', phone).order('created_at', desc=True).limit(3).execute()
            
            if not grievances.data:
                return "You don't have any registered grievances yet.\n\nFeel free to share your concerns and I'll help register them."
            
            status_text = f"📊 Your Recent Grievances:\n\n"
            for idx, g in enumerate(grievances.data, 1):
                status_emoji = {'pending': '⏳', 'in_progress': '🔄', 'resolved': '✅'}.get(g['status'], '📝')
                status_text += f"{idx}. {status_emoji} {g['status'].upper()}\n   Priority: {g['priority']}/10\n   {g['message'][:50]}...\n\n"
            
            return status_text
        
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
        
        priority_label = "🔴 HIGH" if priority >= 8 else "🟡 MEDIUM" if priority >= 5 else "🟢 LOW"
        
        response = f"""✅ Grievance Registered Successfully!

📋 Summary: {summary}

🎯 Category: {category}
⚡ Priority: {priority_label} ({priority}/10)
🔢 Reference ID: {grievance_id[:8].upper()}

Your concern has been registered and will be reviewed by our team within 24-48 hours.

You'll receive updates as we work on resolving this.

Thank you for reaching out! 🙏"""
        
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