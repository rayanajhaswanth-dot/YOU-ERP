"""
YOU - Governance ERP WhatsApp Bot
Complete Grievance Management System with:
- Standardized format extraction
- Multi-turn conversation for missing info
- Dynamic language handling
- AI-driven structuring from unstructured input
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
import base64
import httpx
import random
import string
import re
import subprocess
from datetime import datetime, timezone, timedelta
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContent
from emergentintegrations.llm.openai import OpenAISpeechToText

router = APIRouter()

# Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
STORAGE_BUCKET = os.environ.get('STORAGE_BUCKET', 'Grievances')

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ==============================================================================
# CONVERSATION STATE MANAGEMENT
# In-memory store for multi-turn conversations (production: use Redis)
# ==============================================================================
conversation_states: Dict[str, Dict[str, Any]] = {}

def get_conversation_state(phone: str) -> Dict[str, Any]:
    """Get or create conversation state for a phone number"""
    if phone not in conversation_states:
        conversation_states[phone] = {
            "stage": "greeting",  # greeting, collecting_name, collecting_area, collecting_category, collecting_description, confirming
            "language": "en",
            "collected_data": {
                "name": None,
                "phone": phone,
                "area": None,
                "category": None,
                "description": None,
                "media_url": None
            },
            "last_activity": datetime.now(timezone.utc).isoformat()
        }
    return conversation_states[phone]

def update_conversation_state(phone: str, updates: Dict[str, Any]):
    """Update conversation state"""
    state = get_conversation_state(phone)
    state.update(updates)
    state["last_activity"] = datetime.now(timezone.utc).isoformat()
    conversation_states[phone] = state

def clear_conversation_state(phone: str):
    """Clear conversation state after successful registration"""
    if phone in conversation_states:
        del conversation_states[phone]

# ==============================================================================
# LANGUAGE DETECTION & MULTI-LINGUAL RESPONSES
# ==============================================================================

def detect_language(text: str) -> str:
    """Detect language from text using Unicode script ranges"""
    if not text:
        return "en"
    
    if re.search(r'[\u0C00-\u0C7F]', text): return "te"  # Telugu
    if re.search(r'[\u0900-\u097F]', text): return "hi"  # Hindi
    if re.search(r'[\u0B80-\u0BFF]', text): return "ta"  # Tamil
    if re.search(r'[\u0C80-\u0CFF]', text): return "kn"  # Kannada
    if re.search(r'[\u0D00-\u0D7F]', text): return "ml"  # Malayalam
    if re.search(r'[\u0980-\u09FF]', text): return "bn"  # Bengali
    
    return "en"

# Greeting patterns for all languages
GREETING_PATTERNS = ["hi", "hello", "hey", "namaste", "నమస్కారం", "హాయ్", "హలో", "नमस्ते", "नमस्कार", "हाय", "வணக்கம்", "ನಮಸ್ಕಾರ"]

# 11 Governance Categories (English standard)
CATEGORIES_EN = [
    "Water & Irrigation", "Agriculture", "Forests & Environment",
    "Health & Sanitation", "Education", "Infrastructure & Roads",
    "Law & Order", "Welfare Schemes", "Finance & Taxation",
    "Urban & Rural Development", "Electricity", "Miscellaneous"
]

# Category translations for display
CATEGORY_TRANSLATIONS = {
    "te": {
        "Water & Irrigation": "నీరు & సాగునీరు",
        "Agriculture": "వ్యవసాయం",
        "Health & Sanitation": "ఆరోగ్యం & పారిశుద్ధ్యం",
        "Education": "విద్య",
        "Infrastructure & Roads": "మౌలిక సదుపాయాలు & రోడ్లు",
        "Law & Order": "శాంతిభద్రత",
        "Welfare Schemes": "సంక్షేమ పథకాలు",
        "Electricity": "విద్యుత్",
        "Miscellaneous": "ఇతరాలు"
    },
    "hi": {
        "Water & Irrigation": "जल और सिंचाई",
        "Agriculture": "कृषि",
        "Health & Sanitation": "स्वास्थ्य और स्वच्छता",
        "Education": "शिक्षा",
        "Infrastructure & Roads": "बुनियादी ढांचा और सड़कें",
        "Law & Order": "कानून व्यवस्था",
        "Welfare Schemes": "कल्याण योजनाएं",
        "Electricity": "बिजली",
        "Miscellaneous": "विविध"
    }
}

# Multi-lingual response templates
RESPONSES = {
    "greeting": {
        "en": """🙏 Namaste {name}!

Welcome to the MLA's Grievance Helpline.

To register your grievance, please provide:
1. Your Full Name
2. Contact Number  
3. Area (Village/Mandal/Ward/Town)
4. Issue Category
5. Problem Description

You can also:
• 🎤 Send a voice message
• 📸 Send a photo of the issue
• 📄 Send a document

Type your grievance or say 'help' for assistance.""",

        "te": """🙏 నమస్కారం {name}!

MLA ఫిర్యాదుల హెల్ప్‌లైన్‌కు స్వాగతం.

మీ ఫిర్యాదును నమోదు చేయడానికి, దయచేసి అందించండి:
1. మీ పూర్తి పేరు
2. ఫోన్ నంబర్
3. ప్రాంతం (గ్రామం/మండలం/వార్డు/పట్టణం)
4. సమస్య విభాగం
5. సమస్య వివరణ

మీరు కూడా చేయవచ్చు:
• 🎤 వాయిస్ మెసేజ్ పంపండి
• 📸 సమస్య ఫోటో పంపండి

మీ సమస్యను టైప్ చేయండి లేదా సహాయం కోసం 'help' అని టైప్ చేయండి.""",

        "hi": """🙏 नमस्ते {name}!

MLA शिकायत हेल्पलाइन में आपका स्वागत है।

अपनी शिकायत दर्ज करने के लिए, कृपया दें:
1. आपका पूरा नाम
2. संपर्क नंबर
3. क्षेत्र (गांव/मंडल/वार्ड/शहर)
4. समस्या श्रेणी
5. समस्या विवरण

आप यह भी कर सकते हैं:
• 🎤 वॉयस मैसेज भेजें
• 📸 समस्या की फोटो भेजें

अपनी समस्या टाइप करें या मदद के लिए 'help' टाइप करें।"""
    },
    
    "ask_name": {
        "en": "📝 Please provide your **full name** for the grievance record:",
        "te": "📝 దయచేసి ఫిర్యాదు రికార్డు కోసం మీ **పూర్తి పేరు** అందించండి:",
        "hi": "📝 कृपया शिकायत रिकॉर्ड के लिए अपना **पूरा नाम** दें:"
    },
    
    "ask_area": {
        "en": "📍 Please provide your **area/location**:\n(Village name, Mandal, Ward, Town, or Division)",
        "te": "📍 దయచేసి మీ **ప్రాంతం/స్థానం** అందించండి:\n(గ్రామం పేరు, మండలం, వార్డు, లేదా పట్టణం)",
        "hi": "📍 कृपया अपना **क्षेत्र/स्थान** दें:\n(गांव का नाम, मंडल, वार्ड, या शहर)"
    },
    
    "ask_category": {
        "en": """📁 Please select the **issue category**:

1. Water & Irrigation
2. Agriculture  
3. Health & Sanitation
4. Education
5. Infrastructure & Roads
6. Law & Order
7. Welfare Schemes
8. Electricity
9. Other

Reply with the number or category name.""",

        "te": """📁 దయచేసి **సమస్య విభాగం** ఎంచుకోండి:

1. నీరు & సాగునీరు
2. వ్యవసాయం
3. ఆరోగ్యం & పారిశుద్ధ్యం
4. విద్య
5. మౌలిక సదుపాయాలు & రోడ్లు
6. శాంతిభద్రత
7. సంక్షేమ పథకాలు
8. విద్యుత్
9. ఇతరాలు

సంఖ్య లేదా విభాగం పేరుతో ప్రత్యుత్తరం ఇవ్వండి.""",

        "hi": """📁 कृपया **समस्या श्रेणी** चुनें:

1. जल और सिंचाई
2. कृषि
3. स्वास्थ्य और स्वच्छता
4. शिक्षा
5. बुनियादी ढांचा और सड़कें
6. कानून व्यवस्था
7. कल्याण योजनाएं
8. बिजली
9. अन्य

नंबर या श्रेणी नाम से जवाब दें।"""
    },
    
    "ask_description": {
        "en": "📝 Please describe your **problem/issue** in detail:\n(What happened? Where? When? Any other relevant details)",
        "te": "📝 దయచేసి మీ **సమస్యను** వివరంగా వివరించండి:\n(ఏమి జరిగింది? ఎక్కడ? ఎప్పుడు? ఇతర వివరాలు)",
        "hi": "📝 कृपया अपनी **समस्या** का विस्तार से वर्णन करें:\n(क्या हुआ? कहां? कब? अन्य प्रासंगिक विवरण)"
    },
    
    "confirm_grievance": {
        "en": """📋 **Please confirm your grievance details:**

👤 Name: {name}
📱 Contact: {phone}
📍 Area: {area}
📁 Category: {category}
📝 Issue: {description}

Reply **YES** to confirm and register, or **NO** to make changes.""",

        "te": """📋 **దయచేసి మీ ఫిర్యాదు వివరాలను నిర్ధారించండి:**

👤 పేరు: {name}
📱 ఫోన్: {phone}
📍 ప్రాంతం: {area}
📁 విభాగం: {category}
📝 సమస్య: {description}

నిర్ధారించడానికి **YES** అని, మార్పులు చేయడానికి **NO** అని ప్రత్యుత్తరం ఇవ్వండి.""",

        "hi": """📋 **कृपया अपनी शिकायत विवरण की पुष्टि करें:**

👤 नाम: {name}
📱 संपर्क: {phone}
📍 क्षेत्र: {area}
📁 श्रेणी: {category}
📝 समस्या: {description}

पुष्टि के लिए **YES**, बदलाव के लिए **NO** टाइप करें।"""
    },
    
    "ticket_registered": {
        "en": """✅ **Ticket #{ticket_id} Registered Successfully!**

📅 Date: {date}
⏰ Time: {time}

📁 Category: {category}
⚡ Priority: {priority}

Thank you for contacting the Leader's Office.
You'll receive updates on WhatsApp as we process your grievance.

Type 'status' anytime to check progress.""",

        "te": """✅ **టికెట్ #{ticket_id} విజయవంతంగా నమోదు చేయబడింది!**

📅 తేదీ: {date}
⏰ సమయం: {time}

📁 విభాగం: {category}
⚡ ప్రాధాన్యత: {priority}

నాయకుడి కార్యాలయాన్ని సంప్రదించినందుకు ధన్యవాదాలు.
మీ ఫిర్యాదును ప్రాసెస్ చేస్తున్నప్పుడు WhatsAppలో అప్‌డేట్‌లు అందుతాయి.

పురోగతిని చూడటానికి 'status' అని టైప్ చేయండి.""",

        "hi": """✅ **टिकट #{ticket_id} सफलतापूर्वक पंजीकृत!**

📅 दिनांक: {date}
⏰ समय: {time}

📁 श्रेणी: {category}
⚡ प्राथमिकता: {priority}

नेता के कार्यालय से संपर्क करने के लिए धन्यवाद।
आपकी शिकायत पर कार्रवाई होने पर WhatsApp पर अपडेट मिलेंगे।

प्रगति देखने के लिए 'status' टाइप करें।"""
    },
    
    "voice_error": {
        "en": "🎤 I received your voice message but couldn't transcribe it. Please try again or type your message.",
        "te": "🎤 మీ వాయిస్ మెసేజ్ అందింది కానీ ట్రాన్‌స్క్రైబ్ చేయలేకపోయాను. దయచేసి మళ్ళీ ప్రయత్నించండి లేదా టైప్ చేయండి.",
        "hi": "🎤 मुझे आपका वॉयस मैसेज मिला लेकिन ट्रांसक्राइब नहीं कर सका। कृपया फिर से प्रयास करें या टाइप करें।"
    }
}

def get_response(key: str, lang: str, **kwargs) -> str:
    """Get localized response"""
    templates = RESPONSES.get(key, {})
    template = templates.get(lang, templates.get("en", ""))
    return template.format(**kwargs) if kwargs else template


# ==============================================================================
# AI-DRIVEN INFORMATION EXTRACTION
# ==============================================================================

async def extract_grievance_from_unstructured_text(text: str, lang: str, phone: str, name: str) -> Dict[str, Any]:
    """
    Use AI to extract structured grievance data from unstructured text.
    Even if user provides info in confused/fragmented manner, AI organizes it.
    """
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"extract-{uuid.uuid4()}",
            system_message="""You are an AI assistant that extracts grievance information from unstructured text.
Your job is to identify and extract:
1. Person's name
2. Contact number (if mentioned)
3. Area/Location (Village, Mandal, Ward, Town, City, Division, Panchayat)
4. Issue Category (from: Water & Irrigation, Agriculture, Health & Sanitation, Education, Infrastructure & Roads, Law & Order, Welfare Schemes, Electricity, Miscellaneous)
5. Issue Description

Even if information is mixed, unclear, or fragmented, extract what you can find.
ALWAYS return the category in ENGLISH regardless of input language.

Return ONLY valid JSON (no markdown):
{"name": "extracted name or null", "area": "extracted area or null", "category": "English category name", "description": "cleaned description", "has_all_required": true/false}"""
        ).with_model("gemini", "gemini-2.0-flash")
        
        prompt = f"""Extract grievance information from this message:

MESSAGE: "{text}"
SENDER NAME (from WhatsApp): {name}
SENDER PHONE: {phone}

Extract and organize the information. If the text is in Telugu/Hindi, still return category in English.
If name is not mentioned, use the sender name from WhatsApp.

Return ONLY valid JSON."""
        
        result = await chat.send_message(UserMessage(text=prompt))
        clean_result = result.replace('```json', '').replace('```', '').strip()
        extracted = json.loads(clean_result)
        
        return {
            "name": extracted.get("name") or name,
            "area": extracted.get("area"),
            "category": extracted.get("category", "Miscellaneous"),
            "description": extracted.get("description", text),
            "has_all_required": extracted.get("has_all_required", False)
        }
        
    except Exception as e:
        print(f"⚠️ AI extraction failed: {e}")
        return {
            "name": name,
            "area": None,
            "category": "Miscellaneous",
            "description": text,
            "has_all_required": False
        }


async def analyze_message_intent(message: str, lang: str, conversation_state: Dict) -> Dict[str, Any]:
    """
    Analyze if message is greeting, status request, query, or grievance content.
    Also handles category selection responses.
    """
    message_lower = message.lower().strip()
    
    # Check for greetings
    if any(g in message_lower for g in GREETING_PATTERNS) and len(message_lower) < 20:
        return {"intent": "GREETING"}
    
    # Check for status request
    if message_lower in ['status', 'స్థితి', 'स्थिति', 'check', 'my complaints']:
        return {"intent": "STATUS"}
    
    # Check for help request
    if message_lower in ['help', 'సహాయం', 'मदद', '?']:
        return {"intent": "HELP"}
    
    # Check for confirmation (YES/NO)
    if message_lower in ['yes', 'y', 'అవును', 'हां', 'ha', 'confirm']:
        return {"intent": "CONFIRM_YES"}
    if message_lower in ['no', 'n', 'కాదు', 'नहीं', 'nahi', 'change']:
        return {"intent": "CONFIRM_NO"}
    
    # Check for category number selection
    if message_lower in ['1', '2', '3', '4', '5', '6', '7', '8', '9']:
        category_map = {
            '1': "Water & Irrigation",
            '2': "Agriculture",
            '3': "Health & Sanitation",
            '4': "Education",
            '5': "Infrastructure & Roads",
            '6': "Law & Order",
            '7': "Welfare Schemes",
            '8': "Electricity",
            '9': "Miscellaneous"
        }
        return {"intent": "CATEGORY_SELECTION", "category": category_map.get(message_lower)}
    
    # Default: grievance content
    return {"intent": "GRIEVANCE_CONTENT"}


def categorize_text(text: str) -> tuple:
    """
    Categorize text using keyword matching.
    Returns: (category_en, priority_level, deadline_hours)
    """
    text_lower = text.lower()
    
    # Critical emergency keywords
    critical_keywords = ["fire", "accident", "death", "emergency", "danger", "collapse", "అత్యవసరం", "ప్రమాదం", "आग", "दुर्घटना"]
    if any(k in text_lower for k in critical_keywords):
        return ("Emergency", "CRITICAL", 4)
    
    # Category keywords with more Indian language terms
    CATEGORY_KEYWORDS = {
        "Water & Irrigation": ["water", "irrigation", "borewell", "tank", "drinking", "pipeline", "tap", "నీరు", "నీటి", "बोर", "पानी", "जल"],
        "Agriculture": ["crop", "farmer", "fertilizer", "harvest", "రైతు", "పంట", "किसान", "फसल", "खेती"],
        "Health & Sanitation": ["hospital", "doctor", "medicine", "garbage", "sanitation", "ఆసుపత్రి", "अस्पताल", "डॉक्टर"],
        "Education": ["school", "college", "teacher", "student", "పాఠశాల", "स्कूल", "शिक्षा"],
        "Infrastructure & Roads": ["road", "pothole", "bridge", "street light", "construction", "రోడ్డు", "सड़क", "गड्ढा"],
        "Law & Order": ["police", "theft", "crime", "safety", "పోలీసు", "पुलिस", "चोरी"],
        "Welfare Schemes": ["pension", "ration", "housing", "scheme", "card", "పింఛను", "రేషన్", "पेंशन", "राशन"],
        "Electricity": ["electricity", "power", "current", "transformer", "విద్యుత్", "కరెంట్", "बिजली"],
    }
    
    detected_category = "Miscellaneous"
    max_matches = 0
    
    for category, keywords in CATEGORY_KEYWORDS.items():
        matches = sum(1 for k in keywords if k in text_lower)
        if matches > max_matches:
            max_matches = matches
            detected_category = category
    
    # Priority based on category
    if detected_category in ["Health & Sanitation", "Law & Order", "Electricity"]:
        return (detected_category, "CRITICAL", 4)
    elif detected_category in ["Water & Irrigation", "Infrastructure & Roads", "Agriculture"]:
        return (detected_category, "HIGH", 24)
    elif detected_category in ["Welfare Schemes", "Education"]:
        return (detected_category, "MEDIUM", 72)
    else:
        return (detected_category, "LOW", 336)


# ==============================================================================
# MEDIA PROCESSING
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

import asyncio

async def upload_to_supabase_storage(file_obj: dict, folder: str, client: httpx.AsyncClient) -> str:
    """Upload media to Supabase Storage"""
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
    extension = file_obj['content_type'].split('/')[-1].split(';')[0]
    if extension == 'mpeg': extension = 'mp3'
    
    file_name = f"{folder}/{int(datetime.now().timestamp())}_{random_suffix}.{extension}"
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/{file_name}"
    
    upload_response = await client.post(
        upload_url,
        headers={'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}', 'Content-Type': file_obj['content_type']},
        content=file_obj['buffer'],
        timeout=60.0
    )
    
    if upload_response.status_code not in [200, 201]:
        raise Exception(f"Upload failed: {upload_response.text}")
    
    return f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{file_name}"


async def transcribe_audio(audio_data: bytes, content_type: str) -> str:
    """Transcribe audio using Whisper with FFmpeg conversion"""
    try:
        # Determine format
        original_ext = 'ogg'
        if 'mp3' in content_type: original_ext = 'mp3'
        elif 'wav' in content_type: original_ext = 'wav'
        
        temp_id = str(uuid.uuid4())
        original_path = f"/tmp/audio_{temp_id}.{original_ext}"
        
        with open(original_path, 'wb') as f:
            f.write(audio_data)
        
        # Convert to MP3 if needed
        transcribe_path = original_path
        if original_ext in ['ogg', 'opus', 'amr']:
            mp3_path = f"/tmp/audio_{temp_id}.mp3"
            result = subprocess.run([
                'ffmpeg', '-i', original_path, '-acodec', 'libmp3lame', '-ar', '16000', '-ac', '1', '-y', mp3_path
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                transcribe_path = mp3_path
        
        # Transcribe
        stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
        with open(transcribe_path, 'rb') as audio_file:
            response = await stt.transcribe(file=audio_file, model="whisper-1", response_format="json")
        
        transcript = response.text if hasattr(response, 'text') else str(response)
        
        # Cleanup
        try:
            os.remove(original_path)
            if transcribe_path != original_path:
                os.remove(transcribe_path)
        except: pass
        
        return transcript.strip()
        
    except Exception as e:
        print(f"⚠️ Transcription error: {e}")
        return ""


async def extract_from_image(image_data: bytes) -> Dict[str, Any]:
    """Extract grievance information from image using AI"""
    try:
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"ocr-{uuid.uuid4()}",
            system_message="You are an AI that extracts text and information from images for a government grievance system."
        ).with_model("openai", "gpt-4o")
        
        prompt = """Analyze this image and extract any grievance-related information:
1. Any text (handwritten or printed)
2. Description of visible issues (damaged road, broken pipe, etc.)
3. Location if visible (signboards, landmarks)

Return JSON only:
{"text": "extracted text", "issue_description": "what problem is shown", "location": "if found", "category": "Infrastructure/Water/Health/etc"}"""
        
        msg = UserMessage(text=prompt, file_contents=[FileContent(content_type="image", file_content_base64=image_base64)])
        result = await chat.send_message(msg)
        
        clean_result = result.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_result)
        
    except Exception as e:
        print(f"⚠️ Image extraction error: {e}")
        return {"text": "", "issue_description": "", "location": "", "category": "Miscellaneous"}


async def extract_from_pdf(pdf_data: bytes) -> Dict[str, Any]:
    """Extract grievance information from PDF document using AI"""
    try:
        pdf_base64 = base64.b64encode(pdf_data).decode('utf-8')
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"pdf-{uuid.uuid4()}",
            system_message="You are an AI that extracts grievance information from PDF documents for a government grievance system."
        ).with_model("openai", "gpt-4o")
        
        prompt = """Analyze this PDF document and extract any grievance-related information:
1. Person's name (if mentioned)
2. Contact details (phone, address)
3. Location/Area mentioned
4. Issue or complaint description
5. Any dates or reference numbers

Return JSON only:
{"name": "extracted name or null", "phone": "phone if found or null", "area": "location/area", "issue_description": "main complaint", "category": "Water/Infrastructure/Health/Education/etc"}"""
        
        msg = UserMessage(text=prompt, file_contents=[FileContent(content_type="application/pdf", file_content_base64=pdf_base64)])
        result = await chat.send_message(msg)
        
        clean_result = result.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_result)
        
    except Exception as e:
        print(f"⚠️ PDF extraction error: {e}")
        return {"name": None, "phone": None, "area": None, "issue_description": "", "category": "Miscellaneous"}


# ==============================================================================
# MAIN WEBHOOK HANDLER
# ==============================================================================

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """Main WhatsApp webhook - Multi-turn conversation flow"""
    try:
        form_data = await request.form()
        
        from_number = form_data.get('From', '').replace('whatsapp:', '').strip()
        message_body = form_data.get('Body', '').strip()
        profile_name = form_data.get('ProfileName', 'Citizen')
        
        num_media = int(form_data.get('NumMedia', 0))
        media_url = form_data.get('MediaUrl0', '') if num_media > 0 else None
        media_content_type = form_data.get('MediaContentType0', '') if num_media > 0 else None
        
        print(f"📱 WhatsApp from {from_number} ({profile_name}): {message_body[:100]}...")
        
        response_message = await process_conversation(
            phone=from_number,
            message=message_body,
            name=profile_name,
            media_url=media_url,
            media_content_type=media_content_type
        )
        
        resp = MessagingResponse()
        resp.message(response_message)
        
        from fastapi.responses import Response
        return Response(content=str(resp), media_type="application/xml")
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        import traceback
        traceback.print_exc()
        
        resp = MessagingResponse()
        resp.message("Sorry, I encountered an error. Please try again.")
        
        from fastapi.responses import Response
        return Response(content=str(resp), media_type="application/xml")


async def process_conversation(phone: str, message: str, name: str, media_url: str = None, media_content_type: str = None) -> str:
    """
    Multi-turn conversation flow for grievance collection.
    Ensures all required fields are collected before registration.
    """
    supabase = get_supabase()
    
    # Get current conversation state
    state = get_conversation_state(phone)
    
    # Detect language (and update if user switches)
    detected_lang = detect_language(message)
    if detected_lang != "en":
        state["language"] = detected_lang
        update_conversation_state(phone, {"language": detected_lang})
    
    lang = state["language"]
    
    # Analyze message intent
    intent_result = await analyze_message_intent(message, lang, state)
    intent = intent_result.get("intent")
    
    print(f"🎯 Intent: {intent}, Stage: {state['stage']}, Lang: {lang}")
    
    # ===========================================================================
    # Handle Special Commands
    # ===========================================================================
    
    if intent == "STATUS":
        return await get_grievance_status(phone, lang, supabase)
    
    if intent == "HELP":
        return get_response("greeting", lang, name=name)
    
    # ===========================================================================
    # Process Media (Voice/Image)
    # ===========================================================================
    
    if media_url and media_content_type:
        async with httpx.AsyncClient(timeout=120.0) as client:
            media_obj = await download_twilio_media(media_url, client)
            
            if media_obj:
                is_audio = media_content_type.startswith('audio/') or 'ogg' in media_url.lower()
                is_image = media_content_type.startswith('image/')
                
                # Upload to storage
                try:
                    folder = 'audio' if is_audio else 'images'
                    stored_url = await upload_to_supabase_storage(media_obj, folder, client)
                    state["collected_data"]["media_url"] = stored_url
                except Exception as e:
                    print(f"⚠️ Storage upload failed: {e}")
                
                if is_audio:
                    transcript = await transcribe_audio(media_obj['buffer'], media_content_type)
                    if transcript:
                        message = transcript
                        detected_lang = detect_language(message)
                        if detected_lang != "en":
                            state["language"] = detected_lang
                            lang = detected_lang
                    else:
                        return get_response("voice_error", lang)
                
                elif is_image:
                    extracted = await extract_from_image(media_obj['buffer'])
                    if extracted.get("issue_description"):
                        message = extracted.get("issue_description", "")
                        if extracted.get("location"):
                            state["collected_data"]["area"] = extracted["location"]
                        if extracted.get("category"):
                            state["collected_data"]["category"] = extracted["category"]
                
                # Handle PDF documents
                elif 'pdf' in media_content_type.lower():
                    extracted = await extract_from_pdf(media_obj['buffer'])
                    if extracted.get("issue_description"):
                        message = extracted.get("issue_description", "")
                    if extracted.get("name"):
                        state["collected_data"]["name"] = extracted["name"]
                    if extracted.get("phone"):
                        state["collected_data"]["phone"] = extracted["phone"]
                    if extracted.get("area"):
                        state["collected_data"]["area"] = extracted["area"]
                    if extracted.get("category"):
                        state["collected_data"]["category"] = extracted["category"]
    
    # ===========================================================================
    # Multi-Turn Conversation Flow
    # ===========================================================================
    
    # GREETING - Start new conversation
    if intent == "GREETING" or state["stage"] == "greeting":
        update_conversation_state(phone, {
            "stage": "collecting_info",
            "collected_data": {
                "name": name,
                "phone": phone,
                "area": None,
                "category": None,
                "description": None,
                "media_url": state["collected_data"].get("media_url")
            }
        })
        return get_response("greeting", lang, name=name)
    
    # CONFIRMATION - Yes/No
    if state["stage"] == "confirming":
        if intent == "CONFIRM_YES":
            return await register_grievance(phone, state, lang, supabase)
        elif intent == "CONFIRM_NO":
            update_conversation_state(phone, {"stage": "collecting_info"})
            return get_response("greeting", lang, name=name)
    
    # CATEGORY SELECTION
    if state["stage"] == "collecting_category" and intent == "CATEGORY_SELECTION":
        state["collected_data"]["category"] = intent_result.get("category", "Miscellaneous")
        update_conversation_state(phone, {"collected_data": state["collected_data"]})
        
        # Check if we have everything
        if state["collected_data"]["description"]:
            return await confirm_grievance(phone, state, lang)
        else:
            update_conversation_state(phone, {"stage": "collecting_description"})
            return get_response("ask_description", lang)
    
    # COLLECTING INFO - Use AI to extract from unstructured text
    if state["stage"] in ["collecting_info", "collecting_name", "collecting_area", "collecting_category", "collecting_description"]:
        
        # Try AI extraction from unstructured input
        extracted = await extract_grievance_from_unstructured_text(message, lang, phone, name)
        
        # Update collected data with extracted info
        if extracted.get("name"):
            state["collected_data"]["name"] = extracted["name"]
        if extracted.get("area"):
            state["collected_data"]["area"] = extracted["area"]
        if extracted.get("category") and extracted["category"] != "Miscellaneous":
            state["collected_data"]["category"] = extracted["category"]
        if extracted.get("description"):
            state["collected_data"]["description"] = extracted["description"]
        
        update_conversation_state(phone, {"collected_data": state["collected_data"]})
        
        # Check what's missing and ask for it
        data = state["collected_data"]
        
        if not data.get("name") or data["name"] == "Citizen":
            update_conversation_state(phone, {"stage": "collecting_name"})
            return get_response("ask_name", lang)
        
        if not data.get("area"):
            update_conversation_state(phone, {"stage": "collecting_area"})
            return get_response("ask_area", lang)
        
        if not data.get("category") or data["category"] == "Miscellaneous":
            # Try to auto-detect category from description
            if data.get("description"):
                cat, _, _ = categorize_text(data["description"])
                if cat != "Miscellaneous":
                    data["category"] = cat
                    update_conversation_state(phone, {"collected_data": data})
                else:
                    update_conversation_state(phone, {"stage": "collecting_category"})
                    return get_response("ask_category", lang)
            else:
                update_conversation_state(phone, {"stage": "collecting_category"})
                return get_response("ask_category", lang)
        
        if not data.get("description"):
            update_conversation_state(phone, {"stage": "collecting_description"})
            return get_response("ask_description", lang)
        
        # All data collected - confirm
        return await confirm_grievance(phone, state, lang)
    
    # Default fallback
    return get_response("greeting", lang, name=name)


async def confirm_grievance(phone: str, state: Dict, lang: str) -> str:
    """Show confirmation message with all collected details"""
    data = state["collected_data"]
    
    update_conversation_state(phone, {"stage": "confirming"})
    
    # Get category in user's language for display
    category_display = data.get("category", "Miscellaneous")
    if lang in CATEGORY_TRANSLATIONS and category_display in CATEGORY_TRANSLATIONS[lang]:
        category_display = CATEGORY_TRANSLATIONS[lang][category_display]
    
    return get_response("confirm_grievance", lang,
        name=data.get("name", ""),
        phone=data.get("phone", phone),
        area=data.get("area", ""),
        category=category_display,
        description=data.get("description", "")[:200] + "..." if len(data.get("description", "")) > 200 else data.get("description", "")
    )


async def register_grievance(phone: str, state: Dict, lang: str, supabase) -> str:
    """Register the grievance in database with standardized format"""
    data = state["collected_data"]
    
    # Get politician ID
    politicians = supabase.table('politicians').select('id').limit(1).execute()
    if not politicians.data:
        return "System error. Please contact the office directly."
    
    politician_id = politicians.data[0]['id']
    
    # Determine priority (always use English category for storage)
    category_en = data.get("category", "Miscellaneous")
    _, priority_level, deadline_hours = categorize_text(data.get("description", ""))
    
    # Override with category-based priority
    if category_en in ["Health & Sanitation", "Law & Order", "Electricity"]:
        priority_level = "CRITICAL"
        deadline_hours = 4
    elif category_en in ["Water & Irrigation", "Infrastructure & Roads", "Agriculture"]:
        priority_level = "HIGH"
        deadline_hours = 24
    
    # Calculate deadline
    now = datetime.now(timezone.utc)
    deadline = (now + timedelta(hours=deadline_hours)).isoformat()
    
    # Create grievance record in STANDARDIZED FORMAT
    grievance_data = {
        'id': str(uuid.uuid4()),
        'politician_id': politician_id,
        
        # Standard Format Fields
        'citizen_name': data.get("name", "Anonymous"),
        'citizen_phone': data.get("phone", phone),
        'village': data.get("area", "Not specified"),  # Area field
        'category': category_en,  # ALWAYS in English
        'issue_type': category_en,
        'description': data.get("description", ""),
        
        # AI Reality Matrix
        'priority_level': priority_level,
        'deadline_timestamp': deadline,
        'ai_priority': 8 if priority_level == 'CRITICAL' else 6 if priority_level == 'HIGH' else 4,
        
        # Media
        'media_url': data.get("media_url"),
        
        # Status
        'status': 'PENDING',
        
        # Language preference for future communications
        'language_preference': lang,
        
        'created_at': now.isoformat()
    }
    
    try:
        result = supabase.table('grievances').insert(grievance_data).execute()
        
        if result.data:
            ticket = result.data[0]
            ticket_id = str(ticket['id'])[:8].upper()
            
            # Format date/time for user
            date_str = now.strftime("%d-%m-%Y")
            time_str = now.strftime("%I:%M %p")
            
            # Get category in user's language for display
            category_display = category_en
            if lang in CATEGORY_TRANSLATIONS and category_en in CATEGORY_TRANSLATIONS[lang]:
                category_display = CATEGORY_TRANSLATIONS[lang][category_en]
            
            # Clear conversation state
            clear_conversation_state(phone)
            
            return get_response("ticket_registered", lang,
                ticket_id=ticket_id,
                date=date_str,
                time=time_str,
                category=category_display,
                priority=priority_level
            )
        
    except Exception as e:
        print(f"❌ DB Error: {e}")
    
    return "Error registering grievance. Please try again."


async def get_grievance_status(phone: str, lang: str, supabase) -> str:
    """Get grievance status for user"""
    try:
        result = supabase.table('grievances').select('*').eq('citizen_phone', phone).order('created_at', desc=True).limit(5).execute()
        
        if not result.data:
            if lang == "te":
                return "మీ ఫోన్ నంబర్‌తో ఫిర్యాదులు కనుగొనబడలేదు."
            elif lang == "hi":
                return "आपके फोन नंबर से कोई शिकायत नहीं मिली।"
            return "No grievances found for your number."
        
        status_text = "📊 Your Recent Grievances:\n\n" if lang == "en" else "📊 మీ ఫిర్యాదులు:\n\n" if lang == "te" else "📊 आपकी शिकायतें:\n\n"
        
        for idx, g in enumerate(result.data, 1):
            status_emoji = {'PENDING': '⏳', 'IN_PROGRESS': '🔄', 'RESOLVED': '✅', 'ASSIGNED': '👤'}.get(g.get('status', '').upper(), '📝')
            created = g.get('created_at', '')[:10]
            desc = g.get('description', '')[:50]
            status_text += f"{idx}. {status_emoji} {g.get('status', 'PENDING')}\n   📅 {created}\n   📝 {desc}...\n\n"
        
        return status_text
        
    except Exception as e:
        print(f"❌ Status fetch error: {e}")
        return "Error fetching status. Please try again."


# ==============================================================================
# ADDITIONAL ENDPOINTS
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

@router.get("/status")
async def whatsapp_status():
    """Check WhatsApp bot status"""
    return {
        "status": "active",
        "features": [
            "Multi-turn conversation for complete grievance collection",
            "AI-driven extraction from unstructured text",
            "Dynamic language switching (Telugu, Hindi, Tamil, etc.)",
            "Voice message transcription with FFmpeg conversion",
            "Image/document OCR and extraction",
            "Standardized grievance format",
            "Follow-up questions for missing information"
        ]
    }
