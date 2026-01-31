"""
YOU - Governance ERP WhatsApp Bot
Complete 10-Step Grievance Workflow Implementation
"""
from fastapi import APIRouter, HTTPException, Request
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
import re
from datetime import datetime, timezone, timedelta
from urllib.parse import quote
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContent

router = APIRouter()

# Configuration
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.environ.get('TWILIO_WHATSAPP_NUMBER')
EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')
SARVAM_API_KEY = os.environ.get('SARVAM_API_KEY')
SUPABASE_URL = os.environ.get('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.environ.get('SUPABASE_SERVICE_KEY')
STORAGE_BUCKET = os.environ.get('STORAGE_BUCKET', 'Grievances')

twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# ==============================================================================
# LANGUAGE DETECTION & MULTI-LINGUAL RESPONSES
# ==============================================================================

def detect_language(text: str) -> str:
    """Detect language from text using Unicode script ranges"""
    if not text:
        return "en"
    
    # Telugu: \u0C00-\u0C7F
    if re.search(r'[\u0C00-\u0C7F]', text):
        return "te"
    
    # Hindi/Devanagari: \u0900-\u097F
    if re.search(r'[\u0900-\u097F]', text):
        return "hi"
    
    # Tamil: \u0B80-\u0BFF
    if re.search(r'[\u0B80-\u0BFF]', text):
        return "ta"
    
    # Kannada: \u0C80-\u0CFF
    if re.search(r'[\u0C80-\u0CFF]', text):
        return "kn"
    
    # Malayalam: \u0D00-\u0D7F
    if re.search(r'[\u0D00-\u0D7F]', text):
        return "ml"
    
    # Bengali: \u0980-\u09FF
    if re.search(r'[\u0980-\u09FF]', text):
        return "bn"
    
    # Marathi uses Devanagari, detect by context
    # Gujarati: \u0A80-\u0AFF
    if re.search(r'[\u0A80-\u0AFF]', text):
        return "gu"
    
    # Punjabi/Gurmukhi: \u0A00-\u0A7F
    if re.search(r'[\u0A00-\u0A7F]', text):
        return "pa"
    
    # Odia: \u0B00-\u0B7F
    if re.search(r'[\u0B00-\u0B7F]', text):
        return "or"
    
    return "en"


# Multi-lingual greeting patterns
GREETING_PATTERNS = {
    "en": ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"],
    "hi": ["नमस्ते", "नमस्कार", "हाय", "हेलो", "प्रणाम", "जय हिंद"],
    "te": ["నమస్కారం", "హాయ్", "హలో", "నమస్తే", "ఏంటి", "బాగున్నారా"],
    "ta": ["வணக்கம்", "நமஸ்காரம்", "ஹாய்", "ஹலோ"],
    "kn": ["ನಮಸ್ಕಾರ", "ನಮಸ್ತೆ", "ಹಾಯ್", "ಹಲೋ"],
    "ml": ["നമസ്കാരം", "ഹായ്", "ഹലോ"],
    "bn": ["নমস্কার", "হ্যালো", "হাই"],
    "gu": ["નમસ્તે", "જય શ્રી કૃષ્ણ", "હાય"],
    "pa": ["ਸਤ ਸ੍ਰੀ ਅਕਾਲ", "ਨਮਸਤੇ", "ਹਾਏ"],
    "mr": ["नमस्कार", "नमस्ते", "हाय"],
}

# Multi-lingual response templates
RESPONSES = {
    "greeting": {
        "en": """🙏 Namaste {name}!

Welcome to the MLA's Grievance Helpline.

I'm here to help you register your concerns. You can:
• 📝 Type your grievance/problem
• 🎤 Send a voice message (Hindi, Telugu, Tamil, etc.)
• 📸 Send a photo of the issue

For queries about schemes or policies, just ask me!

Commands:
• Type 'status' to check your complaints
• Type 'help' for more options""",

        "te": """🙏 నమస్కారం {name}!

MLA ఫిర్యాదుల హెల్ప్‌లైన్‌కు స్వాగతం.

మీ సమస్యలను నమోదు చేయడంలో మీకు సహాయం చేయడానికి నేను ఇక్కడ ఉన్నాను.

మీరు:
• 📝 మీ సమస్యను టైప్ చేయండి
• 🎤 వాయిస్ మెసేజ్ పంపండి
• 📸 సమస్య ఫోటో పంపండి

పథకాలు లేదా విధానాల గురించి ప్రశ్నలకు, నన్ను అడగండి!

ఆదేశాలు:
• 'status' అని టైప్ చేసి మీ ఫిర్యాదుల స్థితిని చూడండి""",

        "hi": """🙏 नमस्ते {name}!

MLA शिकायत हेल्पलाइन में आपका स्वागत है।

मैं आपकी समस्याओं को दर्ज करने में मदद के लिए यहां हूं।

आप:
• 📝 अपनी समस्या टाइप करें
• 🎤 वॉयस मैसेज भेजें
• 📸 समस्या की फोटो भेजें

योजनाओं या नीतियों के बारे में सवालों के लिए, मुझसे पूछें!

कमांड:
• 'status' टाइप करके अपनी शिकायतों की स्थिति देखें""",

        "ta": """🙏 வணக்கம் {name}!

MLA புகார் உதவி எண்ணுக்கு வரவேற்கிறோம்.

உங்கள் பிரச்சனைகளை பதிவு செய்ய நான் இங்கே இருக்கிறேன்.

நீங்கள்:
• 📝 உங்கள் பிரச்சனையை டைப் செய்யுங்கள்
• 🎤 குரல் செய்தி அனுப்புங்கள்
• 📸 பிரச்சனையின் புகைப்படம் அனுப்புங்கள்

திட்டங்கள் அல்லது கொள்கைகள் பற்றிய கேள்விகளுக்கு, என்னிடம் கேளுங்கள்!""",

        "kn": """🙏 ನಮಸ್ಕಾರ {name}!

MLA ದೂರು ಸಹಾಯವಾಣಿಗೆ ಸ್ವಾಗತ.

ನಿಮ್ಮ ಸಮಸ್ಯೆಗಳನ್ನು ನೋಂದಾಯಿಸಲು ನಾನು ಇಲ್ಲಿದ್ದೇನೆ.

ನೀವು:
• 📝 ನಿಮ್ಮ ಸಮಸ್ಯೆಯನ್ನು ಟೈಪ್ ಮಾಡಿ
• 🎤 ಧ್ವನಿ ಸಂದೇಶ ಕಳುಹಿಸಿ
• 📸 ಸಮಸ್ಯೆಯ ಫೋಟೋ ಕಳುಹಿಸಿ""",
    },
    
    "out_of_purview": {
        "en": "🙏 I understand your concern, but personal matters like loans, court cases, or job transfers are outside the MLA's official purview.\n\nI can help you with:\n• Infrastructure issues (roads, water, electricity)\n• Government welfare schemes\n• Civic amenities\n• Public services\n\nPlease share a civic grievance and I'll register it immediately.",
        "te": "🙏 మీ ఆందోళన నాకు అర్థమైంది, కానీ వ్యక్తిగత రుణాలు, కోర్టు కేసులు లేదా ఉద్యోగ బదిలీలు వంటి విషయాలు MLA అధికార పరిధిలో లేవు.\n\nనేను సహాయం చేయగలను:\n• మౌలిక సదుపాయాల సమస్యలు (రోడ్లు, నీరు, విద్యుత్)\n• ప్రభుత్వ సంక్షేమ పథకాలు\n• పౌర సౌకర్యాలు\n\nదయచేసి పౌర సమస్యను పంపండి.",
        "hi": "🙏 मैं आपकी चिंता समझता हूं, लेकिन व्यक्तिगत ऋण, अदालती मामले या नौकरी स्थानांतरण जैसे मामले MLA के अधिकार क्षेत्र से बाहर हैं।\n\nमैं मदद कर सकता हूं:\n• बुनियादी ढांचे की समस्याएं (सड़कें, पानी, बिजली)\n• सरकारी कल्याण योजनाएं\n• नागरिक सुविधाएं\n\nकृपया कोई नागरिक शिकायत साझा करें।",
    },
    
    "ticket_registered": {
        "en": """✅ Ticket #{ticket_id} Registered.

📁 Category: {category}
⚡ Priority: {priority}
📋 Status: {status}

Thank you for contacting the Leader's Office.
You'll receive updates as we work on this.""",

        "te": """✅ టికెట్ #{ticket_id} నమోదు చేయబడింది.

📁 విభాగం: {category}
⚡ ప్రాధాన్యత: {priority}
📋 స్థితి: {status}

నాయకుడి కార్యాలయాన్ని సంప్రదించినందుకు ధన్యవాదాలు.
మేము దీనిపై పని చేస్తున్నప్పుడు మీకు అప్‌డేట్‌లు అందుతాయి.""",

        "hi": """✅ टिकट #{ticket_id} पंजीकृत।

📁 श्रेणी: {category}
⚡ प्राथमिकता: {priority}
📋 स्थिति: {status}

नेता के कार्यालय से संपर्क करने के लिए धन्यवाद।
जैसे ही हम इस पर काम करेंगे, आपको अपडेट मिलेंगे।""",
    },
    
    "resolution_message": {
        "en": """✅ Great news! Your grievance (Ticket #{ticket_id}) has been resolved!

🙏 Thank you for giving us the opportunity to serve you.

Please rate our service:
Reply with a number from 1-5:
1️⃣ Poor
2️⃣ Fair
3️⃣ Good
4️⃣ Very Good
5️⃣ Excellent""",

        "te": """✅ శుభవార్త! మీ ఫిర్యాదు (టికెట్ #{ticket_id}) పరిష్కరించబడింది!

🙏 మాకు సేవ చేసే అవకాశం ఇచ్చినందుకు ధన్యవాదాలు.

దయచేసి మా సేవను రేట్ చేయండి:
1-5 నుండి ఒక సంఖ్యతో ప్రత్యుత్తరం ఇవ్వండి:
1️⃣ పేలవం
2️⃣ సరిపడేది
3️⃣ మంచిది
4️⃣ చాలా మంచిది
5️⃣ అద్భుతం""",

        "hi": """✅ खुशखबरी! आपकी शिकायत (टिकट #{ticket_id}) का समाधान हो गया है!

🙏 हमें सेवा का अवसर देने के लिए धन्यवाद।

कृपया हमारी सेवा को रेट करें:
1-5 में से एक नंबर से जवाब दें:
1️⃣ खराब
2️⃣ ठीक-ठाक
3️⃣ अच्छा
4️⃣ बहुत अच्छा
5️⃣ उत्कृष्ट""",
    },
    
    "feedback_thanks": {
        "en": "🙏 Thank you for your feedback! Your rating of {rating}/5 has been recorded.\n\nWe appreciate your trust in us. If you have any other concerns, feel free to reach out anytime.",
        "te": "🙏 మీ అభిప్రాయానికి ధన్యవాదాలు! మీ రేటింగ్ {rating}/5 నమోదు చేయబడింది.\n\nమాపై మీ నమ్మకానికి ధన్యవాదాలు. మరేదైనా సమస్య ఉంటే, ఎప్పుడైనా సంప్రదించండి.",
        "hi": "🙏 आपकी प्रतिक्रिया के लिए धन्यवाद! आपकी {rating}/5 रेटिंग दर्ज कर ली गई है।\n\nहम पर आपके विश्वास की सराहना करते हैं। अगर कोई और समस्या हो, तो कभी भी संपर्क करें।",
    }
}

# Out of purview keywords (personal/private matters)
OUT_OF_PURVIEW_KEYWORDS = [
    "personal loan", "loan", "money", "debt", "court case", "police bail",
    "divorce", "private dispute", "transfer", "promotion", "job offer",
    "personal financial", "loan waiver", "dowry", "marriage", "family dispute",
    "salary", "increment", "bank loan", "home loan", "car loan"
]

# 11-Sector Governance Categories
CATEGORY_KEYWORDS = {
    "Water & Irrigation": ["water", "irrigation", "canal", "borewell", "tank", "drinking", "pipeline", "నీరు", "నీటి", "पानी", "जल"],
    "Agriculture": ["crop", "seed", "farmer", "fertilizer", "msp", "drought", "harvest", "grain", "రైతు", "పంట", "किसान", "फसल"],
    "Forests & Environment": ["forest", "tree", "pollution", "waste", "dumping", "environment", "plastic", "అడవి", "जंगल", "प्रदूषण"],
    "Health & Sanitation": ["hospital", "doctor", "medicine", "dengue", "garbage", "sanitation", "clean", "drain", "mosquito", "ఆసుపత్రి", "अस्पताल", "डॉक्टर"],
    "Education": ["school", "college", "teacher", "student", "exam", "book", "scholarship", "midday meal", "పాఠశాల", "स्कूल", "शिक्षा"],
    "Infrastructure & Roads": ["road", "pothole", "bridge", "building", "street light", "construction", "cement", "రోడ్డు", "सड़क", "पुल"],
    "Law & Order": ["police", "theft", "crime", "safety", "fight", "harassment", "illegal", "పోలీసు", "पुलिस", "चोरी"],
    "Welfare Schemes": ["pension", "ration", "housing", "scheme", "aadhaar", "beneficiary", "support", "పింఛను", "రేషన్", "पेंशन", "राशन"],
    "Finance & Taxation": ["tax", "funds", "budget", "finance", "gst", "పన్ను", "कर", "बजट"],
    "Urban & Rural Development": ["panchayat", "municipality", "park", "community hall", "development", "permit", "పంచాయతీ", "पंचायत"],
}


def get_response(key: str, lang: str, **kwargs) -> str:
    """Get localized response, falling back to English"""
    templates = RESPONSES.get(key, {})
    template = templates.get(lang, templates.get("en", ""))
    return template.format(**kwargs) if kwargs else template


def is_greeting(text: str, lang: str) -> bool:
    """Check if text is a greeting in any language"""
    text_lower = text.lower().strip()
    
    # Check all language patterns
    for patterns in GREETING_PATTERNS.values():
        for pattern in patterns:
            if pattern.lower() in text_lower or text_lower in pattern.lower():
                return True
    return False


def is_out_of_purview(text: str) -> bool:
    """Check if request is outside MLA's purview"""
    text_lower = text.lower()
    return any(keyword in text_lower for keyword in OUT_OF_PURVIEW_KEYWORDS)


def categorize_grievance(text: str) -> tuple:
    """
    Categorize grievance using 11-Sector Framework
    Returns: (category, priority_level, deadline_hours)
    """
    text_lower = text.lower()
    
    # Emergency keywords - CRITICAL priority
    critical_keywords = ["fire", "accident", "current", "open wire", "shock", "danger", "emergency", "అత్యవసరం", "आग", "दुर्घटना"]
    if any(k in text_lower for k in critical_keywords):
        return ("Emergency", "CRITICAL", 4)
    
    # Detect category
    detected_category = "Miscellaneous"
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(k in text_lower for k in keywords):
            detected_category = category
            break
    
    # Priority based on category
    if detected_category in ["Health & Sanitation", "Law & Order"]:
        return (detected_category, "CRITICAL", 4)
    elif detected_category in ["Water & Irrigation", "Infrastructure & Roads", "Agriculture"]:
        return (detected_category, "HIGH", 24)
    elif detected_category in ["Welfare Schemes", "Education"]:
        return (detected_category, "MEDIUM", 72)
    else:
        return (detected_category, "LOW", 336)


# ==============================================================================
# SESSION MANAGEMENT - Store conversation state
# ==============================================================================

async def get_or_create_constituent(phone: str, name: str) -> dict:
    """Get or create constituent record for session management"""
    supabase = get_supabase()
    
    # Try to find existing constituent
    result = supabase.table('constituents').select('*').eq('phone', phone).execute()
    
    if result.data:
        return result.data[0]
    
    # Create new constituent
    constituent_data = {
        'id': str(uuid.uuid4()),
        'phone': phone,
        'name': name,
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    try:
        insert_result = supabase.table('constituents').insert(constituent_data).execute()
        return insert_result.data[0] if insert_result.data else constituent_data
    except Exception as e:
        print(f"⚠️ Could not create constituent record: {e}")
        return constituent_data


async def get_pending_feedback_ticket(phone: str) -> dict:
    """Check if user has a recently resolved ticket awaiting feedback"""
    supabase = get_supabase()
    
    # Look for resolved tickets without feedback rating from this phone
    result = supabase.table('grievances').select('*').ilike('village', f'%{phone}%').eq('status', 'RESOLVED').is_('feedback_rating', 'null').order('created_at', desc=True).limit(1).execute()
    
    return result.data[0] if result.data else None


# ==============================================================================
# MEDIA HELPERS
# ==============================================================================

async def download_twilio_media(url: str, client: httpx.AsyncClient) -> dict:
    """Download media from Twilio with authentication"""
    import asyncio
    
    if not url:
        return None
    
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
    max_retries = 3
    
    for attempt in range(max_retries):
        try:
            response = await client.get(url, auth=auth, follow_redirects=True, timeout=60.0)
            
            if response.status_code == 200 and len(response.content) > 0:
                content_type = response.headers.get('content-type', 'application/octet-stream')
                if 'xml' not in content_type.lower():
                    return {'buffer': response.content, 'content_type': content_type}
            
            if response.status_code == 404 and attempt < max_retries - 1:
                await asyncio.sleep(2)
                continue
                
        except Exception as e:
            if attempt < max_retries - 1:
                await asyncio.sleep(2)
                continue
            raise
    
    return None


async def upload_to_supabase_storage(file_obj: dict, folder: str, client: httpx.AsyncClient) -> str:
    """Upload media to Supabase Storage and return signed URL"""
    random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=7))
    extension = file_obj['content_type'].split('/')[-1].split(';')[0]
    if extension == 'mpeg':
        extension = 'mp3'
    
    file_name = f"{folder}/{int(datetime.now().timestamp())}_{random_suffix}.{extension}"
    upload_url = f"{SUPABASE_URL}/storage/v1/object/{STORAGE_BUCKET}/{file_name}"
    
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
        raise Exception(f"Upload failed: {upload_response.text}")
    
    # Generate signed URL
    sign_url = f"{SUPABASE_URL}/storage/v1/object/sign/{STORAGE_BUCKET}/{file_name}"
    sign_response = await client.post(
        sign_url,
        headers={
            'Authorization': f'Bearer {SUPABASE_SERVICE_KEY}',
            'Content-Type': 'application/json'
        },
        json={"expiresIn": 604800},  # 7 days
        timeout=30.0
    )
    
    if sign_response.status_code == 200:
        sign_data = sign_response.json()
        return f"{SUPABASE_URL}/storage/v1{sign_data.get('signedURL', '')}"
    
    return f"{SUPABASE_URL}/storage/v1/object/public/{STORAGE_BUCKET}/{file_name}"


# ==============================================================================
# AI INTENT DETECTION
# ==============================================================================

async def analyze_message_intent(message: str, lang: str, name: str) -> dict:
    """
    Use AI to determine if message is:
    - GREETING: Just saying hello
    - QUERY: Asking about schemes, policies, procedures
    - GRIEVANCE: Reporting a problem that needs action
    - FOLLOWUP: Asking about existing complaint status
    - FEEDBACK: Rating (1-5)
    - THANKS: Expressing gratitude
    """
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"intent-{uuid.uuid4()}",
            system_message="""You are an intelligent assistant for an Indian MLA's (Member of Legislative Assembly) office.
Your job is to classify citizen messages and respond appropriately.

IMPORTANT RULES:
1. If someone asks about government schemes, welfare programs, policies - this is a QUERY (not grievance)
2. If someone reports a problem like "no water", "road damaged", "electricity cut" - this is a GRIEVANCE
3. If someone just says hello/hi in any language - this is a GREETING
4. Respond in the same language the citizen used
5. For QUERIES about schemes, provide accurate, helpful information
6. Never register informational queries as grievances"""
        ).with_model("gemini", "gemini-2.0-flash")
        
        prompt = f"""Analyze this message from a citizen (Name: {name}):

MESSAGE: "{message}"
DETECTED LANGUAGE: {lang}

Classify the intent and respond:

1. GREETING - If just saying hello/hi/namaste etc in any language
2. QUERY - If asking about schemes, policies, procedures, requirements, eligibility, how-to questions
   Examples: "What is Rajiv Gandhi Yuva scheme?", "How to apply for pension?", "Documents needed for ration card?"
3. GRIEVANCE - If reporting an actual problem needing action
   Examples: "No water in our area", "Road has potholes", "Street light not working"
4. FOLLOWUP - If asking about status of existing complaint
5. FEEDBACK - If it's a rating number (1-5)
6. THANKS - If expressing gratitude

For QUERY type, provide a helpful, accurate response about the scheme/policy.
For GREETING, provide a warm welcome response in the citizen's language.

Respond with ONLY valid JSON (no markdown):
{{"intent": "GREETING|QUERY|GRIEVANCE|FOLLOWUP|FEEDBACK|THANKS", "response": "your helpful response in the same language as the message", "category": "if grievance, the category", "priority": "if grievance, CRITICAL/HIGH/MEDIUM/LOW"}}"""

        user_msg = UserMessage(text=prompt)
        result = await chat.send_message(user_msg)
        
        # Parse response
        clean_result = result.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_result)
        
    except Exception as e:
        print(f"⚠️ AI intent detection failed: {e}")
        return {"intent": "GRIEVANCE", "response": "", "category": "Miscellaneous", "priority": "MEDIUM"}


# ==============================================================================
# MAIN WEBHOOK HANDLER
# ==============================================================================

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """Main WhatsApp webhook - handles all incoming messages"""
    try:
        form_data = await request.form()
        
        from_number = form_data.get('From', '')
        message_body = form_data.get('Body', '').strip()
        profile_name = form_data.get('ProfileName', 'Citizen')
        
        # Media handling
        num_media = int(form_data.get('NumMedia', 0))
        media_url = form_data.get('MediaUrl0', '') if num_media > 0 else None
        media_content_type = form_data.get('MediaContentType0', '') if num_media > 0 else None
        
        phone_clean = from_number.replace('whatsapp:', '').strip()
        
        print(f"📱 WhatsApp from {phone_clean} ({profile_name}): {message_body[:100]}...")
        print(f"   Media: {num_media} files, Type: {media_content_type}")
        
        # Process the message
        response_message = await process_message(
            phone=phone_clean,
            message=message_body,
            name=profile_name,
            media_url=media_url,
            media_content_type=media_content_type
        )
        
        print(f"📤 Response: {response_message[:100]}...")
        
        # Build TwiML response
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


async def process_message(phone: str, message: str, name: str, media_url: str = None, media_content_type: str = None) -> str:
    """
    Main message processing logic implementing the 10-step workflow
    """
    supabase = get_supabase()
    
    # Detect language from message
    lang = detect_language(message)
    print(f"🌐 Detected language: {lang}")
    
    # Get or create constituent record
    constituent = await get_or_create_constituent(phone, name)
    
    # ===========================================================================
    # STEP 1: Check if user is providing FEEDBACK RATING (1-5)
    # ===========================================================================
    if message.strip() in ['1', '2', '3', '4', '5']:
        rating = int(message.strip())
        
        # Find the most recent resolved ticket awaiting feedback
        pending_ticket = await get_pending_feedback_ticket(phone)
        
        if pending_ticket:
            # Update the ticket with feedback rating
            supabase.table('grievances').update({
                'feedback_rating': rating
            }).eq('id', pending_ticket['id']).execute()
            
            return get_response("feedback_thanks", lang, rating=rating)
        else:
            # No pending feedback, might be a grievance with just a number
            pass
    
    # ===========================================================================
    # STEP 2: Handle GREETING (hi, hello, నమస్కారం, etc.)
    # ===========================================================================
    if is_greeting(message, lang) and not media_url:
        return get_response("greeting", lang, name=name)
    
    # ===========================================================================
    # STEP 3: Handle STATUS command
    # ===========================================================================
    if message.lower().strip() in ['status', 'స్థితి', 'स्थिति', 'check', 'my complaints']:
        grievances = supabase.table('grievances').select('*').ilike('village', f'%{phone}%').order('created_at', desc=True).limit(5).execute()
        
        if not grievances.data:
            if lang == "te":
                return "మీ ఫోన్ నంబర్‌తో ఎటువంటి ఫిర్యాదులు కనుగొనబడలేదు.\n\nమీ సమస్యను పంపండి, నేను దానిని నమోదు చేస్తాను."
            elif lang == "hi":
                return "आपके फोन नंबर से कोई शिकायत नहीं मिली।\n\nअपनी समस्या भेजें, मैं इसे दर्ज करूंगा।"
            return "No grievances found for your number.\n\nShare your concern and I'll register it."
        
        status_text = "📊 Your Recent Grievances:\n\n" if lang == "en" else "📊 మీ ఇటీవలి ఫిర్యాదులు:\n\n" if lang == "te" else "📊 आपकी हाल की शिकायतें:\n\n"
        
        for idx, g in enumerate(grievances.data, 1):
            status_emoji = {'PENDING': '⏳', 'IN_PROGRESS': '🔄', 'RESOLVED': '✅', 'ASSIGNED': '👤'}.get(g.get('status', '').upper(), '📝')
            desc = g.get('description', 'No description')[:50]
            created = g.get('created_at', '')[:10]
            status_text += f"{idx}. {status_emoji} {g.get('status', 'PENDING')}\n   📅 {created}\n   📝 {desc}...\n\n"
        
        return status_text
    
    # ===========================================================================
    # STEP 4: Handle HELP command
    # ===========================================================================
    if message.lower().strip() in ['help', 'సహాయం', 'मदद', 'commands']:
        if lang == "te":
            return "📋 ఎలా ఉపయోగించాలి:\n\n1. మీ సమస్యను టైప్ చేయండి\n2. లేదా వాయిస్ మెసేజ్ పంపండి 🎤\n3. లేదా సమస్య ఫోటో పంపండి 📸\n\n'status' టైప్ చేసి మీ ఫిర్యాదుల స్థితిని చూడండి"
        elif lang == "hi":
            return "📋 कैसे उपयोग करें:\n\n1. अपनी समस्या टाइप करें\n2. या वॉयस मैसेज भेजें 🎤\n3. या समस्या की फोटो भेजें 📸\n\n'status' टाइप करके अपनी शिकायतों की स्थिति देखें"
        return "📋 How to use:\n\n1. Type your problem/grievance\n2. OR send a voice message 🎤\n3. OR send a photo of the issue 📸\n\nType 'status' to check your grievances"
    
    # ===========================================================================
    # STEP 5: Handle TICKET CLOSURE (by OSD/PA)
    # ===========================================================================
    if message.lower().startswith("fixed_") or message.lower().startswith("resolved_"):
        parts = message.split("_")
        if len(parts) >= 2:
            ticket_id = parts[1].strip()
            
            update_result = supabase.table('grievances').update({
                'status': 'RESOLVED'
            }).eq('id', ticket_id).execute()
            
            if update_result.data:
                # Get citizen phone to send resolution message
                ticket = update_result.data[0]
                citizen_phone = ticket.get('citizen_phone') or phone
                ticket_lang = ticket.get('language_preference', 'en')
                
                return f"✅ Ticket #{ticket_id[:8].upper()} marked as RESOLVED.\n\n📋 Resolution notification will be sent to the citizen."
            else:
                return "❌ Could not find that ticket ID."
    
    # ===========================================================================
    # STEP 6: Process MEDIA (Voice/Image)
    # ===========================================================================
    voice_transcript = None
    image_analysis = None
    stored_media_url = None
    
    if media_url and media_content_type:
        is_audio = media_content_type.startswith('audio/') or any(ext in media_url.lower() for ext in ['.ogg', '.mp3', '.wav', '.m4a', '.opus', '.amr'])
        is_image = media_content_type.startswith('image/') or any(ext in media_url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp'])
        
        try:
            async with httpx.AsyncClient(timeout=120.0) as client:
                media_obj = await download_twilio_media(media_url, client)
                
                if media_obj:
                    # Upload to storage
                    try:
                        folder = 'audio' if is_audio else 'images'
                        stored_media_url = await upload_to_supabase_storage(media_obj, folder, client)
                    except Exception as e:
                        print(f"⚠️ Storage upload failed: {e}")
                    
                    # Process audio
                    if is_audio:
                        try:
                            from emergentintegrations.llm.openai import OpenAISpeechToText
                            
                            temp_path = f"/tmp/audio_{uuid.uuid4()}.ogg"
                            with open(temp_path, 'wb') as f:
                                f.write(media_obj['buffer'])
                            
                            stt = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
                            
                            with open(temp_path, 'rb') as audio_file:
                                response = await stt.transcribe(
                                    file=audio_file,
                                    model="whisper-1",
                                    response_format="json"
                                )
                            
                            voice_transcript = response.text if hasattr(response, 'text') else str(response)
                            message = voice_transcript  # Replace message with transcript
                            lang = detect_language(message)  # Re-detect language
                            
                            print(f"🎤 Transcribed: {voice_transcript[:100]}...")
                            
                            try:
                                os.remove(temp_path)
                            except:
                                pass
                                
                        except Exception as e:
                            print(f"⚠️ Whisper failed: {e}")
                            return "🎤 I received your voice message but couldn't transcribe it. Please try:\n• Speaking clearly\n• Recording again\n• Or typing your message"
                    
                    # Process image
                    elif is_image:
                        try:
                            image_base64 = base64.b64encode(media_obj['buffer']).decode('utf-8')
                            
                            vision_chat = LlmChat(
                                api_key=EMERGENT_LLM_KEY,
                                session_id=f"vision-{uuid.uuid4()}",
                                system_message="You are analyzing images for a government grievance system. Extract text and identify issues."
                            ).with_model("openai", "gpt-4o")
                            
                            vision_prompt = """Analyze this image. It may be:
1. A handwritten letter/complaint
2. A photo of damaged infrastructure (road, water pipe, etc.)
3. A document or form

Extract:
- Any text (OCR)
- Description of any visible issues
- Location if mentioned

Respond with JSON only:
{"text": "extracted text", "issue": "description of issue", "location": "if found", "category": "Infrastructure/Water/Health/etc"}"""
                            
                            vision_msg = UserMessage(
                                text=vision_prompt,
                                file_contents=[FileContent(content_type="image", file_content_base64=image_base64)]
                            )
                            
                            result = await vision_chat.send_message(vision_msg)
                            clean_result = result.replace('```json', '').replace('```', '').strip()
                            image_analysis = json.loads(clean_result)
                            
                            message = image_analysis.get('issue') or image_analysis.get('text') or message
                            
                        except Exception as e:
                            print(f"⚠️ Image analysis failed: {e}")
                            
        except Exception as e:
            print(f"⚠️ Media processing error: {e}")
    
    # ===========================================================================
    # STEP 7: Check OUT OF PURVIEW
    # ===========================================================================
    if is_out_of_purview(message):
        return get_response("out_of_purview", lang)
    
    # ===========================================================================
    # STEP 8: AI INTENT DETECTION
    # ===========================================================================
    intent_result = await analyze_message_intent(message, lang, name)
    intent = intent_result.get('intent', 'GRIEVANCE').upper()
    ai_response = intent_result.get('response', '')
    
    print(f"🎯 Detected intent: {intent}")
    
    # Handle non-grievance intents
    if intent == "GREETING":
        return ai_response or get_response("greeting", lang, name=name)
    
    elif intent == "QUERY":
        # This is an informational query, not a grievance
        if ai_response:
            return f"📝 {ai_response}\n\n💡 If you have a specific problem that needs action, please describe it and I'll register it as a grievance."
        else:
            return "I understand you have a question. Please provide more details and I'll try to help.\n\nFor problems needing action (water, roads, electricity issues), please describe them clearly."
    
    elif intent == "FOLLOWUP":
        return await process_message(phone, "status", name, None, None)
    
    elif intent == "THANKS":
        if lang == "te":
            return f"🙏 మీకు స్వాగతం, {name}!\n\nమరేదైనా సమస్య ఉంటే, ఎప్పుడైనా సంప్రదించండి."
        elif lang == "hi":
            return f"🙏 आपका स्वागत है, {name}!\n\nअगर कोई और समस्या हो, तो कभी भी संपर्क करें।"
        return f"🙏 You're welcome, {name}!\n\nIf you have any other concerns, feel free to reach out."
    
    # ===========================================================================
    # STEP 9: REGISTER GRIEVANCE
    # ===========================================================================
    
    # Get politician ID
    politicians = supabase.table('politicians').select('id').limit(1).execute()
    if not politicians.data:
        return "System configuration error. Please contact support."
    
    politician_id = politicians.data[0]['id']
    
    # Categorize the grievance
    category, priority_level, deadline_hours = categorize_grievance(message)
    
    # Override with AI detection if available
    if intent_result.get('category'):
        category = intent_result.get('category')
    if intent_result.get('priority'):
        priority_level = intent_result.get('priority')
    
    # Calculate deadline
    deadline_timestamp = (datetime.now(timezone.utc) + timedelta(hours=deadline_hours)).isoformat()
    
    # Build grievance record matching ALL DB columns
    grievance_data = {
        'id': str(uuid.uuid4()),
        'politician_id': politician_id,
        
        # Citizen Info
        'citizen_name': name,
        'citizen_phone': phone,
        
        # Location (store phone in village for backward compatibility)
        'village': f'From {name} ({phone})',
        
        # Core content
        'description': message,
        'category': category,
        'issue_type': category,
        
        # AI Reality Matrix
        'priority_level': priority_level,
        'deadline_timestamp': deadline_timestamp,
        'ai_priority': 8 if priority_level == 'CRITICAL' else 6 if priority_level == 'HIGH' else 4,
        
        # Media
        'media_url': stored_media_url,
        
        # Status
        'status': 'PENDING',
        
        # Language for future communications
        'language_preference': lang,
        
        'created_at': datetime.now(timezone.utc).isoformat()
    }
    
    # Insert grievance
    try:
        insert_result = supabase.table('grievances').insert(grievance_data).execute()
        
        if insert_result.data:
            ticket = insert_result.data[0]
            ticket_id = str(ticket['id'])[:8].upper()
            
            # Format status message
            status_map = {
                "CRITICAL": "🔴 Immediate Action Required",
                "HIGH": "🟠 Priority Queue (24 hrs)",
                "MEDIUM": "🟡 Routine Queue (7 days)",
                "LOW": "🔵 General Queue"
            }
            status_msg = status_map.get(priority_level, "📋 Registered")
            
            return get_response("ticket_registered", lang, 
                ticket_id=ticket_id,
                category=category,
                priority=priority_level,
                status=status_msg
            )
        else:
            ticket_id = str(uuid.uuid4())[:8].upper()
            return get_response("ticket_registered", lang,
                ticket_id=ticket_id,
                category=category,
                priority=priority_level,
                status="📋 Registered"
            )
            
    except Exception as e:
        print(f"❌ DB Error: {e}")
        return "I received your grievance but encountered an error saving it. Please try again or contact the office directly."


# ==============================================================================
# ADDITIONAL ENDPOINTS
# ==============================================================================

class WhatsAppMessage(BaseModel):
    to: str
    message: str


@router.post("/send")
async def send_whatsapp_message(data: WhatsAppMessage):
    """Send WhatsApp message via Twilio"""
    try:
        to_number = data.to if data.to.startswith('whatsapp:') else f'whatsapp:{data.to}'
        
        message = twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=data.message,
            to=to_number
        )
        
        return {"success": True, "message_sid": message.sid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/send-resolution")
async def send_resolution_notification(grievance_id: str):
    """Send resolution notification to citizen and request feedback"""
    supabase = get_supabase()
    
    grievance = supabase.table('grievances').select('*').eq('id', grievance_id).execute()
    
    if not grievance.data:
        raise HTTPException(status_code=404, detail="Grievance not found")
    
    g = grievance.data[0]
    phone = g.get('citizen_phone') or g.get('phone')
    lang = g.get('language_preference', 'en')
    ticket_id = str(g['id'])[:8].upper()
    
    if not phone:
        raise HTTPException(status_code=400, detail="No phone number found")
    
    message = get_response("resolution_message", lang, ticket_id=ticket_id)
    
    try:
        to_number = f'whatsapp:{phone}'
        twilio_client.messages.create(
            from_=TWILIO_WHATSAPP_NUMBER,
            body=message,
            to=to_number
        )
        return {"success": True, "message": "Resolution notification sent"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def whatsapp_status():
    """Check WhatsApp bot status"""
    return {
        "status": "active",
        "twilio_configured": bool(TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN),
        "whatsapp_number": TWILIO_WHATSAPP_NUMBER,
        "features": [
            "Multi-lingual support (Telugu, Hindi, Tamil, Kannada, etc.)",
            "Voice message transcription (Whisper)",
            "Image/document OCR (GPT-4o)",
            "AI intent detection",
            "11-sector categorization",
            "Feedback rating system"
        ]
    }
