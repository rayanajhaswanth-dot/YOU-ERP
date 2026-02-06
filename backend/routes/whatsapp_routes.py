"""
YOU - Governance ERP WhatsApp Bot
CTO MANDATE: Dynamic Language Interceptor, Intelligent Media Processing, Conversational Flow
Updated: 2026-02-06
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
import asyncio
from datetime import datetime, timezone, timedelta
from fastapi.responses import Response

# Import from centralized AI routes
from routes.ai_routes import (
    detect_language,
    translate_text,
    extract_grievance_from_media,
    extract_grievance_from_text,
    transcribe_audio,
    categorize_text,
    is_status_request,
    is_yes_response,
    is_no_response,
    is_greeting,
    is_help_request,
    get_localized_keyword,
    OFFICIAL_CATEGORIES,
    map_to_official_category
)

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
# ==============================================================================
conversation_states: Dict[str, Dict[str, Any]] = {}

def get_conversation_state(phone: str) -> Dict[str, Any]:
    """Get or create conversation state for a phone number"""
    if phone not in conversation_states:
        conversation_states[phone] = {
            "stage": "greeting",
            "language": "en",  # Will be updated dynamically
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
# MULTILINGUAL RESPONSE TEMPLATES
# ==============================================================================

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
• 📄 Send a PDF document

Type your grievance or say '{help_word}' for assistance.""",

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
• 📄 PDF పత్రం పంపండి

మీ సమస్యను టైప్ చేయండి లేదా '{help_word}' అని టైప్ చేయండి.""",

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
• 📄 PDF दस्तावेज़ भेजें

अपनी समस्या टाइप करें या '{help_word}' टाइप करें।""",

        "ta": """🙏 வணக்கம் {name}!

MLA புகார் உதவி எண்ணுக்கு வரவேற்கிறோம்.

உங்கள் புகாரைப் பதிவு செய்ய, தயவுசெய்து வழங்கவும்:
1. உங்கள் முழு பெயர்
2. தொடர்பு எண்
3. பகுதி (கிராமம்/மண்டலம்/வார்டு/நகரம்)
4. பிரச்சனை வகை
5. பிரச்சனை விவரம்

'{help_word}' என்று தட்டச்சு செய்யவும்."""
    },
    
    "ask_name": {
        "en": "📝 Please provide your **full name** for the grievance record:",
        "te": "📝 దయచేసి ఫిర్యాదు రికార్డు కోసం మీ **పూర్తి పేరు** అందించండి:",
        "hi": "📝 कृपया शिकायत रिकॉर्ड के लिए अपना **पूरा नाम** दें:",
        "ta": "📝 புகார் பதிவுக்கு உங்கள் **முழு பெயரை** வழங்கவும்:"
    },
    
    "ask_area": {
        "en": "📍 Please provide your **area/location**:\n(Village name, Mandal, Ward, Town, or Division)",
        "te": "📍 దయచేసి మీ **ప్రాంతం/స్థానం** అందించండి:\n(గ్రామం పేరు, మండలం, వార్డు, లేదా పట్టణం)",
        "hi": "📍 कृपया अपना **क्षेत्र/स्थान** दें:\n(गांव का नाम, मंडल, वार्ड, या शहर)",
        "ta": "📍 உங்கள் **பகுதி/இடத்தை** வழங்கவும்:\n(கிராமம், மண்டலம், வார்டு, நகரம்)"
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

नंबर या श्रेणी नाम से जवाब दें।""",

        "ta": """📁 **பிரச்சனை வகையை** தேர்ந்தெடுக்கவும்:

1. நீர் & நீர்ப்பாசனம்
2. விவசாயம்
3. சுகாதாரம்
4. கல்வி
5. உள்கட்டமைப்பு
6. சட்டம் & ஒழுங்கு
7. நலத்திட்டங்கள்
8. மின்சாரம்
9. மற்றவை

எண் அல்லது வகை பெயரை பதிலளிக்கவும்."""
    },
    
    "ask_description": {
        "en": "📝 Please describe your **problem/issue** in detail:\n(What happened? Where? When? Any other relevant details)",
        "te": "📝 దయచేసి మీ **సమస్యను** వివరంగా వివరించండి:\n(ఏమి జరిగింది? ఎక్కడ? ఎప్పుడు? ఇతర వివరాలు)",
        "hi": "📝 कृपया अपनी **समस्या** का विस्तार से वर्णन करें:\n(क्या हुआ? कहां? कब? अन्य प्रासंगिक विवरण)",
        "ta": "📝 உங்கள் **பிரச்சனையை** விரிவாக விவரிக்கவும்:\n(என்ன நடந்தது? எங்கே? எப்போது?)"
    },
    
    "confirm_grievance": {
        "en": """📋 **Please confirm your grievance details:**

👤 Name: {name}
📱 Contact: {phone}
📍 Area: {area}
📁 Category: {category}
📝 Issue: {description}

Reply **{yes_word}** to confirm and register, or **{no_word}** to make changes.""",

        "te": """📋 **దయచేసి మీ ఫిర్యాదు వివరాలను నిర్ధారించండి:**

👤 పేరు: {name}
📱 ఫోన్: {phone}
📍 ప్రాంతం: {area}
📁 విభాగం: {category}
📝 సమస్య: {description}

నిర్ధారించడానికి **{yes_word}** అని, మార్పులు చేయడానికి **{no_word}** అని ప్రత్యుత్తరం ఇవ్వండి.""",

        "hi": """📋 **कृपया अपनी शिकायत विवरण की पुष्टि करें:**

👤 नाम: {name}
📱 संपर्क: {phone}
📍 क्षेत्र: {area}
📁 श्रेणी: {category}
📝 समस्या: {description}

पुष्टि के लिए **{yes_word}**, बदलाव के लिए **{no_word}** टाइप करें।""",

        "ta": """📋 **உங்கள் புகார் விவரங்களை உறுதிப்படுத்தவும்:**

👤 பெயர்: {name}
📱 தொடர்பு: {phone}
📍 பகுதி: {area}
📁 வகை: {category}
📝 பிரச்சனை: {description}

உறுதிப்படுத்த **{yes_word}**, மாற்ற **{no_word}** தட்டச்சு செய்யவும்."""
    },
    
    "ticket_registered": {
        "en": """✅ **Ticket #{ticket_id} Registered Successfully!**

📅 Date: {date}
⏰ Time: {time}

📁 Category: {category}
⚡ Priority: {priority}

Thank you for contacting the Leader's Office.
You'll receive updates on WhatsApp as we process your grievance.

Type '{status_word}' anytime to check progress.""",

        "te": """✅ **టికెట్ #{ticket_id} విజయవంతంగా నమోదు చేయబడింది!**

📅 తేదీ: {date}
⏰ సమయం: {time}

📁 విభాగం: {category}
⚡ ప్రాధాన్యత: {priority}

నాయకుడి కార్యాలయాన్ని సంప్రదించినందుకు ధన్యవాదాలు.
మీ ఫిర్యాదును ప్రాసెస్ చేస్తున్నప్పుడు WhatsAppలో అప్‌డేట్‌లు అందుతాయి.

పురోగతిని చూడటానికి '{status_word}' అని టైప్ చేయండి.""",

        "hi": """✅ **टिकट #{ticket_id} सफलतापूर्वक पंजीकृत!**

📅 दिनांक: {date}
⏰ समय: {time}

📁 श्रेणी: {category}
⚡ प्राथमिकता: {priority}

नेता के कार्यालय से संपर्क करने के लिए धन्यवाद।
आपकी शिकायत पर कार्रवाई होने पर WhatsApp पर अपडेट मिलेंगे।

प्रगति देखने के लिए '{status_word}' टाइप करें।""",

        "ta": """✅ **டிக்கெட் #{ticket_id} வெற்றிகரமாக பதிவு செய்யப்பட்டது!**

📅 தேதி: {date}
⏰ நேரம்: {time}

📁 வகை: {category}
⚡ முன்னுரிமை: {priority}

தலைவர் அலுவலகத்தை தொடர்புகொண்டதற்கு நன்றி.
நிலையை பார்க்க '{status_word}' தட்டச்சு செய்யவும்."""
    },
    
    "voice_received": {
        "en": "🎤 I received your voice message and transcribed it. Processing your grievance...",
        "te": "🎤 మీ వాయిస్ మెసేజ్ అందింది, ట్రాన్‌స్క్రైబ్ చేయబడింది. మీ ఫిర్యాదును ప్రాసెస్ చేస్తున్నాను...",
        "hi": "🎤 मुझे आपका वॉयस मैसेज मिला और ट्रांसक्राइब हो गया। आपकी शिकायत प्रोसेस हो रही है...",
        "ta": "🎤 உங்கள் குரல் செய்தி பெறப்பட்டது. உங்கள் புகார் செயலாக்கப்படுகிறது..."
    },
    
    "voice_error": {
        "en": "🎤 I received your voice message but couldn't transcribe it. Please try again or type your message.",
        "te": "🎤 మీ వాయిస్ మెసేజ్ అందింది కానీ ట్రాన్‌స్క్రైబ్ చేయలేకపోయాను. దయచేసి మళ్ళీ ప్రయత్నించండి లేదా టైప్ చేయండి.",
        "hi": "🎤 मुझे आपका वॉयस मैसेज मिला लेकिन ट्रांसक्राइब नहीं कर सका। कृपया फिर से प्रयास करें या टाइप करें.",
        "ta": "🎤 குரல் செய்தி பெறப்பட்டது ஆனால் படியெடுக்க முடியவில்லை. மீண்டும் முயற்சிக்கவும்."
    },
    
    "media_received": {
        "en": "📎 I received your {media_type} and extracted the information. Processing your grievance...",
        "te": "📎 మీ {media_type} అందింది, సమాచారం సేకరించబడింది. మీ ఫిర్యాదును ప్రాసెస్ చేస్తున్నాను...",
        "hi": "📎 आपका {media_type} मिला और जानकारी निकाली गई। आपकी शिकायत प्रोसेस हो रही है...",
        "ta": "📎 உங்கள் {media_type} பெறப்பட்டது. உங்கள் புகார் செயலாக்கப்படுகிறது..."
    },
    
    "media_error": {
        "en": "📎 I received your file but couldn't extract information. Please describe your issue in text.",
        "te": "📎 మీ ఫైల్ అందింది కానీ సమాచారం సేకరించలేకపోయాను. దయచేసి మీ సమస్యను టెక్స్ట్‌లో వివరించండి.",
        "hi": "📎 आपकी फाइल मिली लेकिन जानकारी नहीं निकाल सका। कृपया अपनी समस्या टेक्स्ट में बताएं.",
        "ta": "📎 உங்கள் கோப்பு பெறப்பட்டது ஆனால் தகவல் பெற முடியவில்லை. உங்கள் பிரச்சனையை உரையில் விவரிக்கவும்."
    },
    
    "status_response": {
        "en": "📊 **Your Recent Grievances:**\n\n",
        "te": "📊 **మీ ఇటీవలి ఫిర్యాదులు:**\n\n",
        "hi": "📊 **आपकी हालिया शिकायतें:**\n\n",
        "ta": "📊 **உங்கள் சமீபத்திய புகார்கள்:**\n\n"
    },
    
    "no_grievances": {
        "en": "No grievances found for your phone number.",
        "te": "మీ ఫోన్ నంబర్‌తో ఫిర్యాదులు కనుగొనబడలేదు.",
        "hi": "आपके फोन नंबर से कोई शिकायत नहीं मिली।",
        "ta": "உங்கள் தொலைபேசி எண்ணில் புகார்கள் இல்லை."
    },
    
    "clarification_needed": {
        "en": "I couldn't fully understand your request. Could you please provide more details about your issue?",
        "te": "మీ అభ్యర్థనను పూర్తిగా అర్థం చేసుకోలేకపోయాను. దయచేసి మీ సమస్య గురించి మరిన్ని వివరాలు అందించగలరా?",
        "hi": "मैं आपके अनुरोध को पूरी तरह समझ नहीं पाया। कृपया अपनी समस्या के बारे में और विवरण दें।",
        "ta": "உங்கள் கோரிக்கையை முழுமையாக புரிந்துகொள்ள முடியவில்லை. உங்கள் பிரச்சனை பற்றி மேலும் விவரங்கள் தரவும்."
    }
}

# Category translations for display (user-facing only, DB always English)
CATEGORY_DISPLAY = {
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
    },
    "ta": {
        "Water & Irrigation": "நீர் & நீர்ப்பாசனம்",
        "Agriculture": "விவசாயம்",
        "Health & Sanitation": "சுகாதாரம்",
        "Education": "கல்வி",
        "Infrastructure & Roads": "உள்கட்டமைப்பு",
        "Law & Order": "சட்டம் & ஒழுங்கு",
        "Welfare Schemes": "நலத்திட்டங்கள்",
        "Electricity": "மின்சாரம்",
        "Miscellaneous": "மற்றவை"
    }
}


def get_response(key: str, lang: str, **kwargs) -> str:
    """Get localized response with dynamic keyword substitution"""
    templates = RESPONSES.get(key, {})
    template = templates.get(lang, templates.get("en", ""))
    
    # Add localized keywords
    kwargs.setdefault('help_word', get_localized_keyword('help', lang) if lang != 'en' else 'help')
    kwargs.setdefault('status_word', get_localized_keyword('status', lang))
    kwargs.setdefault('yes_word', get_localized_keyword('yes', lang))
    kwargs.setdefault('no_word', get_localized_keyword('no', lang))
    
    return template.format(**kwargs) if kwargs else template


def get_category_display(category_en: str, lang: str) -> str:
    """Get category name in user's language for display"""
    if lang == 'en':
        return category_en
    return CATEGORY_DISPLAY.get(lang, {}).get(category_en, category_en)


# ==============================================================================
# MEDIA PROCESSING HELPERS
# ==============================================================================

async def download_twilio_media(url: str, client: httpx.AsyncClient) -> dict:
    """Download media from Twilio with authentication"""
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


async def upload_to_supabase_storage(file_obj: dict, folder: str, client: httpx.AsyncClient) -> str:
    """Upload media to Supabase Storage and return public URL"""
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


# ==============================================================================
# MAIN WEBHOOK HANDLER
# ==============================================================================

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    """Main WhatsApp webhook - Intelligent Multi-turn Conversation"""
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
        
        return Response(content=str(resp), media_type="application/xml")
        
    except Exception as e:
        print(f"❌ Webhook error: {e}")
        import traceback
        traceback.print_exc()
        
        resp = MessagingResponse()
        resp.message("Sorry, I encountered an error. Please try again.")
        
        return Response(content=str(resp), media_type="application/xml")


async def process_conversation(phone: str, message: str, name: str, media_url: str = None, media_content_type: str = None) -> str:
    """
    Intelligent Multi-turn Conversation Flow
    
    Key Features:
    1. Dynamic Language Detection on EVERY message
    2. All responses in user's detected language
    3. Media (PDF/Image) extraction with AI
    4. Database storage ALWAYS in English
    """
    supabase = get_supabase()
    
    # Get conversation state
    state = get_conversation_state(phone)
    
    # =========================================================================
    # STEP 1: LANGUAGE INTERCEPTION (Every message)
    # =========================================================================
    detected_lang = detect_language(message) if message else state["language"]
    
    # Update language if changed mid-conversation
    if detected_lang != state["language"]:
        print(f"🌐 Language switch detected: {state['language']} → {detected_lang}")
        state["language"] = detected_lang
        update_conversation_state(phone, {"language": detected_lang})
    
    lang = state["language"]
    
    # =========================================================================
    # STEP 2: HANDLE MEDIA (PDF/Image/Audio)
    # =========================================================================
    media_extracted_data = None
    
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
                    stored_url = await upload_to_supabase_storage(media_obj, folder, client)
                    state["collected_data"]["media_url"] = stored_url
                except Exception as e:
                    print(f"⚠️ Storage upload failed: {e}")
                
                # Process based on media type
                if is_audio:
                    # Transcribe audio
                    transcript = await transcribe_audio(media_obj['buffer'], media_content_type)
                    if transcript:
                        message = transcript
                        detected_lang = detect_language(message)
                        state["language"] = detected_lang
                        lang = detected_lang
                        print(f"🎤 Transcribed ({lang}): {transcript[:100]}...")
                    else:
                        return get_response("voice_error", lang)
                
                elif is_image or is_pdf:
                    # Extract grievance info from media using AI
                    media_extracted_data = await extract_grievance_from_media(
                        media_obj['buffer'], 
                        media_content_type
                    )
                    
                    if media_extracted_data and media_extracted_data.get("description"):
                        # Update state with extracted data
                        if media_extracted_data.get("name"):
                            state["collected_data"]["name"] = media_extracted_data["name"]
                        if media_extracted_data.get("contact"):
                            state["collected_data"]["phone"] = media_extracted_data["contact"]
                        if media_extracted_data.get("area"):
                            state["collected_data"]["area"] = media_extracted_data["area"]
                        if media_extracted_data.get("category"):
                            state["collected_data"]["category"] = media_extracted_data["category"]
                        if media_extracted_data.get("description"):
                            state["collected_data"]["description"] = media_extracted_data["description"]
                        
                        # Set language from extraction
                        if media_extracted_data.get("language"):
                            lang = media_extracted_data["language"]
                            state["language"] = lang
                        
                        update_conversation_state(phone, {"collected_data": state["collected_data"], "language": lang})
                        
                        media_type_display = "PDF document" if is_pdf else "photo"
                        print(f"📎 Extracted from {media_type_display}: {media_extracted_data}")
                    else:
                        return get_response("media_error", lang)
    
    # =========================================================================
    # STEP 3: CHECK FOR SPECIAL COMMANDS (Multilingual)
    # =========================================================================
    
    # STATUS request
    if is_status_request(message, lang):
        return await get_grievance_status(phone, lang, supabase)
    
    # HELP request
    if is_help_request(message, lang):
        return get_response("greeting", lang, name=name)
    
    # YES confirmation
    if state["stage"] == "confirming" and is_yes_response(message, lang):
        return await register_grievance(phone, state, lang, supabase)
    
    # NO - restart
    if state["stage"] == "confirming" and is_no_response(message, lang):
        update_conversation_state(phone, {"stage": "collecting_info"})
        return get_response("greeting", lang, name=name)
    
    # Category selection by number
    if state["stage"] == "collecting_category" and message.strip() in ['1','2','3','4','5','6','7','8','9']:
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
        state["collected_data"]["category"] = category_map.get(message.strip(), "Miscellaneous")
        update_conversation_state(phone, {"collected_data": state["collected_data"]})
        
        if state["collected_data"]["description"]:
            return await confirm_grievance(phone, state, lang)
        else:
            update_conversation_state(phone, {"stage": "collecting_description"})
            return get_response("ask_description", lang)
    
    # =========================================================================
    # STEP 4: GREETING - Start new conversation
    # =========================================================================
    if is_greeting(message, lang) or state["stage"] == "greeting":
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
    
    # =========================================================================
    # STEP 5: PROCESS GRIEVANCE TEXT
    # =========================================================================
    if state["stage"] in ["collecting_info", "collecting_name", "collecting_area", "collecting_category", "collecting_description"]:
        
        # If we have media-extracted data, use it directly
        if media_extracted_data and media_extracted_data.get("description"):
            data = state["collected_data"]
            # Check what's still missing
            if not data.get("name") or data["name"] == "Citizen":
                data["name"] = name
            
            # If we have all required info from media, go to confirmation
            if data.get("area") and data.get("description"):
                update_conversation_state(phone, {"collected_data": data})
                return await confirm_grievance(phone, state, lang)
        
        # Use AI to extract from unstructured text
        if message:
            extracted = await extract_grievance_from_text(message, name, phone)
            
            # Update collected data with extracted info
            if extracted.get("name") and extracted["name"] != "Citizen":
                state["collected_data"]["name"] = extracted["name"]
            if extracted.get("area"):
                state["collected_data"]["area"] = extracted["area"]
            if extracted.get("category") and extracted["category"] != "Miscellaneous":
                state["collected_data"]["category"] = extracted["category"]
            if extracted.get("description"):
                state["collected_data"]["description"] = extracted["description"]
            
            update_conversation_state(phone, {"collected_data": state["collected_data"]})
        
        # Check what's missing and ask
        data = state["collected_data"]
        
        if not data.get("name") or data["name"] == "Citizen":
            update_conversation_state(phone, {"stage": "collecting_name"})
            return get_response("ask_name", lang)
        
        if not data.get("area"):
            update_conversation_state(phone, {"stage": "collecting_area"})
            return get_response("ask_area", lang)
        
        if not data.get("category") or data["category"] == "Miscellaneous":
            # Try to auto-detect from description
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
    
    # Default fallback - ask for clarification in user's language
    return get_response("clarification_needed", lang)


async def confirm_grievance(phone: str, state: Dict, lang: str) -> str:
    """Show confirmation in user's language with localized YES/NO"""
    data = state["collected_data"]
    
    update_conversation_state(phone, {"stage": "confirming"})
    
    # Get category display in user's language
    category_display = get_category_display(data.get("category", "Miscellaneous"), lang)
    
    # Truncate description for display
    desc = data.get("description", "")
    desc_display = desc[:200] + "..." if len(desc) > 200 else desc
    
    return get_response("confirm_grievance", lang,
        name=data.get("name", ""),
        phone=data.get("phone", phone),
        area=data.get("area", ""),
        category=category_display,
        description=desc_display
    )


async def register_grievance(phone: str, state: Dict, lang: str, supabase) -> str:
    """
    Register grievance in database.
    CRITICAL: All data stored in ENGLISH regardless of input language.
    """
    data = state["collected_data"]
    
    # Get politician ID
    politicians = supabase.table('politicians').select('id').limit(1).execute()
    if not politicians.data:
        return "System error. Please contact the office directly."
    
    politician_id = politicians.data[0]['id']
    
    # Category is ALWAYS in English (enforced by AI extraction)
    category_en = data.get("category", "Miscellaneous")
    if category_en not in OFFICIAL_CATEGORIES:
        category_en = map_to_official_category(category_en)
    
    # Determine priority
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
    
    # Create grievance record - ALL FIELDS IN ENGLISH
    grievance_data = {
        'id': str(uuid.uuid4()),
        'politician_id': politician_id,
        
        # Citizen info
        'citizen_name': data.get("name", "Anonymous"),
        'citizen_phone': data.get("phone", phone),
        
        # Location
        'village': data.get("area", "Not specified"),
        
        # Category - ALWAYS ENGLISH
        'category': category_en,
        'issue_type': category_en,
        
        # Description - Should be English (AI translates during extraction)
        'description': data.get("description", ""),
        
        # AI Reality Matrix
        'priority_level': priority_level,
        'deadline_timestamp': deadline,
        'ai_priority': 8 if priority_level == 'CRITICAL' else 6 if priority_level == 'HIGH' else 4,
        
        # Media
        'media_url': data.get("media_url"),
        
        # Status
        'status': 'PENDING',
        
        # Language for future communications
        'language_preference': lang,
        
        'created_at': now.isoformat()
    }
    
    try:
        result = supabase.table('grievances').insert(grievance_data).execute()
        
        if result.data:
            ticket = result.data[0]
            ticket_id = str(ticket['id'])[:8].upper()
            
            # Format date/time
            date_str = now.strftime("%d-%m-%Y")
            time_str = now.strftime("%I:%M %p")
            
            # Get category display in user's language
            category_display = get_category_display(category_en, lang)
            
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
        import traceback
        traceback.print_exc()
    
    return "Error registering grievance. Please try again."


async def get_grievance_status(phone: str, lang: str, supabase) -> str:
    """Get grievance status in user's language"""
    try:
        result = supabase.table('grievances').select('*').eq('citizen_phone', phone).order('created_at', desc=True).limit(5).execute()
        
        if not result.data:
            return get_response("no_grievances", lang)
        
        status_text = get_response("status_response", lang)
        
        status_emojis = {'PENDING': '⏳', 'IN_PROGRESS': '🔄', 'RESOLVED': '✅', 'ASSIGNED': '👤'}
        
        for idx, g in enumerate(result.data, 1):
            status = g.get('status', 'PENDING').upper()
            emoji = status_emojis.get(status, '📝')
            created = g.get('created_at', '')[:10]
            category = get_category_display(g.get('category', 'Miscellaneous'), lang)
            desc = g.get('description', '')[:50]
            
            status_text += f"{idx}. {emoji} **{status}**\n"
            status_text += f"   📁 {category}\n"
            status_text += f"   📅 {created}\n"
            status_text += f"   📝 {desc}...\n\n"
        
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


@router.post("/send-resolution")
async def send_resolution_notification(grievance_id: str):
    """Send resolution notification to citizen"""
    try:
        supabase = get_supabase()
        result = supabase.table('grievances').select('*').eq('id', grievance_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="Grievance not found")
        
        grievance = result.data[0]
        citizen_phone = grievance.get('citizen_phone')
        lang = grievance.get('language_preference', 'en')
        
        if not citizen_phone:
            raise HTTPException(status_code=400, detail="No phone number for citizen")
        
        # Send notification in citizen's preferred language
        messages = {
            'en': f"✅ Great news! Your grievance #{grievance_id[:8].upper()} has been RESOLVED. Thank you for your patience. Please rate our service by replying with a number 1-5 (5 being excellent).",
            'te': f"✅ శుభవార్త! మీ ఫిర్యాదు #{grievance_id[:8].upper()} పరిష్కరించబడింది. మీ ఓపికకు ధన్యవాదాలు. దయచేసి 1-5 సంఖ్యతో మా సేవను రేట్ చేయండి.",
            'hi': f"✅ खुशखबरी! आपकी शिकायत #{grievance_id[:8].upper()} का समाधान हो गया है। आपके धैर्य के लिए धन्यवाद। कृपया 1-5 अंक देकर हमारी सेवा का मूल्यांकन करें।"
        }
        
        message_text = messages.get(lang, messages['en'])
        
        to_number = f'whatsapp:{citizen_phone}' if not citizen_phone.startswith('whatsapp:') else citizen_phone
        twilio_client.messages.create(from_=TWILIO_WHATSAPP_NUMBER, body=message_text, to=to_number)
        
        return {"success": True, "message": "Resolution notification sent"}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status")
async def whatsapp_status():
    """Check WhatsApp bot status"""
    return {
        "status": "active",
        "version": "2.0 - CTO Mandate Implementation",
        "features": [
            "Dynamic Language Interception (detects language on EVERY message)",
            "Multilingual Responses (Telugu, Hindi, Tamil, Kannada, Malayalam, Bengali)",
            "Localized Keywords (status/yes/no in user's language)",
            "AI-Powered PDF Extraction (GPT-4o)",
            "AI-Powered Image OCR (GPT-4o)",
            "Voice Transcription with FFmpeg (Whisper)",
            "Standardized English Categories (11 Official)",
            "Multi-turn Contextual Conversation",
            "Follow-up Questions for Missing Information"
        ],
        "categories": OFFICIAL_CATEGORIES
    }
