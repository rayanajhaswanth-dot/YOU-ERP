"""
YOU - Governance ERP AI Routes
CTO MANDATE: Intelligent Media Extraction, Language Detection, Translation
Updated: 2026-02-06
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Dict, Any
from auth import get_current_user, TokenData
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContent
from emergentintegrations.llm.openai import OpenAISpeechToText
from datetime import datetime, timedelta, timezone
import os
import asyncio
import tempfile
import subprocess
import uuid
import json
import re
import httpx
import base64

router = APIRouter()

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# ==============================================================================
# 11 OFFICIAL GOVERNANCE CATEGORIES (ENGLISH ONLY - NON-NEGOTIABLE)
# ==============================================================================
OFFICIAL_CATEGORIES = [
    "Water & Irrigation",
    "Agriculture", 
    "Forests & Environment",
    "Health & Sanitation",
    "Education",
    "Infrastructure & Roads",
    "Law & Order",
    "Welfare Schemes",
    "Finance & Taxation",
    "Urban & Rural Development",
    "Electricity",
    "Miscellaneous"
]

# ==============================================================================
# LANGUAGE DETECTION & TRANSLATION (FRUGAL - NO LLM FOR SIMPLE DETECTION)
# ==============================================================================

# Unicode script ranges for Indian languages
LANGUAGE_SCRIPTS = {
    'te': (0x0C00, 0x0C7F),  # Telugu
    'hi': (0x0900, 0x097F),  # Hindi/Devanagari
    'ta': (0x0B80, 0x0BFF),  # Tamil
    'kn': (0x0C80, 0x0CFF),  # Kannada
    'ml': (0x0D00, 0x0D7F),  # Malayalam
    'bn': (0x0980, 0x09FF),  # Bengali
    'gu': (0x0A80, 0x0AFF),  # Gujarati
    'mr': (0x0900, 0x097F),  # Marathi (Devanagari)
    'pa': (0x0A00, 0x0A7F),  # Punjabi/Gurmukhi
}

# Multilingual keyword mappings
STATUS_KEYWORDS = {
    'en': ['status', 'check', 'progress', 'update'],
    'te': ['స్టేటస్', 'స్థితి', 'పురోగతి', 'తనిఖీ'],
    'hi': ['स्थिति', 'स्टेटस', 'जांच', 'प्रगति'],
    'ta': ['நிலை', 'சரிபார்'],
    'kn': ['ಸ್ಥಿತಿ', 'ಪರಿಶೀಲಿಸಿ'],
    'ml': ['സ്ഥിതി', 'പരിശോധിക്കുക'],
    'bn': ['অবস্থা', 'চেক'],
}

YES_KEYWORDS = {
    'en': ['yes', 'y', 'confirm', 'ok', 'okay'],
    'te': ['అవును', 'హాఁ', 'సరే', 'ఓకే'],
    'hi': ['हां', 'हाँ', 'जी', 'ठीक', 'ओके'],
    'ta': ['ஆம்', 'சரி'],
    'kn': ['ಹೌದು', 'ಸರಿ'],
    'ml': ['അതെ', 'ശരി'],
    'bn': ['হ্যাঁ', 'ঠিক'],
}

NO_KEYWORDS = {
    'en': ['no', 'n', 'cancel', 'change'],
    'te': ['కాదు', 'లేదు', 'వద్దు', 'మార్చు'],
    'hi': ['नहीं', 'ना', 'रद्द', 'बदलें'],
    'ta': ['இல்லை', 'வேண்டாம்'],
    'kn': ['ಇಲ್ಲ', 'ಬೇಡ'],
    'ml': ['ഇല്ല', 'വേണ്ട'],
    'bn': ['না', 'বাতিল'],
}

GREETING_KEYWORDS = {
    'en': ['hi', 'hello', 'hey', 'good morning', 'good evening'],
    'te': ['నమస్కారం', 'హాయ్', 'హలో'],
    'hi': ['नमस्ते', 'नमस्कार', 'हाय', 'हैलो'],
    'ta': ['வணக்கம்'],
    'kn': ['ನಮಸ್ಕಾರ'],
    'ml': ['നമസ്കാരം'],
    'bn': ['নমস্কার'],
}

HELP_KEYWORDS = {
    'en': ['help', 'assist', 'support', '?'],
    'te': ['సహాయం', 'హెల్ప్'],
    'hi': ['मदद', 'सहायता', 'हेल्प'],
    'ta': ['உதவி'],
    'kn': ['ಸಹಾಯ'],
    'ml': ['സഹായം'],
    'bn': ['সাহায্য'],
}


def detect_language(text: str) -> str:
    """
    Detect language using Unicode script ranges (FRUGAL - no LLM call).
    Returns ISO 639-1 code: 'en', 'te', 'hi', 'ta', 'kn', 'ml', 'bn', etc.
    """
    if not text:
        return 'en'
    
    # Count characters by script
    script_counts = {lang: 0 for lang in LANGUAGE_SCRIPTS}
    total_alpha = 0
    
    for char in text:
        code = ord(char)
        if char.isalpha():
            total_alpha += 1
            for lang, (start, end) in LANGUAGE_SCRIPTS.items():
                if start <= code <= end:
                    script_counts[lang] += 1
                    break
    
    if total_alpha == 0:
        return 'en'
    
    # Find dominant script
    max_lang = max(script_counts, key=script_counts.get)
    max_count = script_counts[max_lang]
    
    # If significant non-English characters detected
    if max_count > total_alpha * 0.2:  # At least 20% in that script
        return max_lang
    
    return 'en'


def is_status_request(text: str, lang: str = None) -> bool:
    """Check if message is a status request in any language"""
    text_lower = text.lower().strip()
    for lang_code, keywords in STATUS_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return True
    return False


def is_yes_response(text: str, lang: str = None) -> bool:
    """Check if message is a YES/confirmation in any language"""
    text_lower = text.lower().strip()
    for lang_code, keywords in YES_KEYWORDS.items():
        if text_lower in keywords or any(text_lower == kw for kw in keywords):
            return True
    return False


def is_no_response(text: str, lang: str = None) -> bool:
    """Check if message is a NO/cancel in any language"""
    text_lower = text.lower().strip()
    for lang_code, keywords in NO_KEYWORDS.items():
        if text_lower in keywords or any(text_lower == kw for kw in keywords):
            return True
    return False


def is_greeting(text: str, lang: str = None) -> bool:
    """Check if message is a greeting in any language"""
    text_lower = text.lower().strip()
    # Short greetings only
    if len(text_lower) > 30:
        return False
    for lang_code, keywords in GREETING_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return True
    return False


def is_help_request(text: str, lang: str = None) -> bool:
    """Check if message is a help request in any language"""
    text_lower = text.lower().strip()
    for lang_code, keywords in HELP_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            return True
    return False


def get_localized_keyword(keyword_type: str, lang: str) -> str:
    """Get keyword in user's language"""
    keyword_maps = {
        'status': STATUS_KEYWORDS,
        'yes': YES_KEYWORDS,
        'no': NO_KEYWORDS,
    }
    
    keyword_map = keyword_maps.get(keyword_type, {})
    keywords = keyword_map.get(lang, keyword_map.get('en', ['']))
    return keywords[0] if keywords else keyword_type


# ==============================================================================
# TRANSLATION SERVICE (Uses LLM only when necessary)
# ==============================================================================

async def translate_text(text: str, target_lang: str, context: str = "grievance system") -> str:
    """
    Translate text to target language using Gemini (frugal model).
    Uses LLM only for actual translation needs.
    """
    if target_lang == 'en':
        return text  # No translation needed
    
    lang_names = {
        'te': 'Telugu',
        'hi': 'Hindi', 
        'ta': 'Tamil',
        'kn': 'Kannada',
        'ml': 'Malayalam',
        'bn': 'Bengali',
        'gu': 'Gujarati',
        'mr': 'Marathi',
        'pa': 'Punjabi',
    }
    
    target_name = lang_names.get(target_lang, 'the local language')
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"translate-{uuid.uuid4()}",
            system_message=f"You are a translator for a government {context}. Translate the given text to {target_name}. Only return the translated text, nothing else."
        ).with_model("gemini", "gemini-2.0-flash")
        
        result = await chat.send_message(UserMessage(text=f"Translate to {target_name}: {text}"))
        return result.strip()
    except Exception as e:
        print(f"⚠️ Translation failed: {e}")
        return text


# ==============================================================================
# INTELLIGENT MEDIA EXTRACTION (PDF/IMAGE)
# ==============================================================================

async def extract_grievance_from_media(media_data: bytes, media_type: str) -> Dict[str, Any]:
    """
    Extract grievance data from PDF or Image using GPT-4o.
    CRITICAL: Must return exactly 6 fields with category in ENGLISH.
    
    Returns:
        {
            "name": str or None,
            "contact": str or None,
            "area": str or None,
            "category": str (ENGLISH ONLY - from 11 official categories),
            "description": str,
            "language": str (detected language code)
        }
    """
    try:
        media_base64 = base64.b64encode(media_data).decode('utf-8')
        
        # Determine content type for FileContent
        if 'pdf' in media_type.lower():
            content_type = "application/pdf"
        elif 'png' in media_type.lower():
            content_type = "image/png"
        else:
            content_type = "image/jpeg"
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"media-extract-{uuid.uuid4()}",
            system_message="""You are an AI assistant for a government grievance system in India.
Your task is to extract structured information from documents and images.

CRITICAL RULES:
1. ALWAYS return the category in ENGLISH from this exact list:
   - Water & Irrigation
   - Agriculture
   - Forests & Environment
   - Health & Sanitation
   - Education
   - Infrastructure & Roads
   - Law & Order
   - Welfare Schemes
   - Finance & Taxation
   - Urban & Rural Development
   - Electricity
   - Miscellaneous

2. Extract ALL 6 fields even if some are null
3. If handwritten, OCR carefully
4. Detect the language of the original document"""
        ).with_model("openai", "gpt-4o")
        
        prompt = """Analyze this document/image and extract grievance information.

REQUIRED OUTPUT (JSON only, no markdown):
{
    "name": "person's full name if found, or null",
    "contact": "phone number if found (10 digits), or null",
    "area": "location/village/town/mandal/ward if found, or null",
    "category": "ENGLISH category from official list",
    "description": "detailed description of the issue/complaint in ENGLISH",
    "language": "detected language code (en/te/hi/ta/kn/ml/bn)"
}

IMPORTANT:
- Category MUST be from: Water & Irrigation, Agriculture, Forests & Environment, Health & Sanitation, Education, Infrastructure & Roads, Law & Order, Welfare Schemes, Finance & Taxation, Urban & Rural Development, Electricity, Miscellaneous
- Description should be translated to ENGLISH for database storage
- If document is in Telugu/Hindi/Tamil etc., still return category and description in English"""
        
        msg = UserMessage(
            text=prompt, 
            file_contents=[FileContent(content_type=content_type, file_content_base64=media_base64)]
        )
        
        result = await chat.send_message(msg)
        
        # Parse JSON response
        clean_result = result.replace('```json', '').replace('```', '').strip()
        extracted = json.loads(clean_result)
        
        # Validate and normalize category
        category = extracted.get("category", "Miscellaneous")
        if category not in OFFICIAL_CATEGORIES:
            # Try to map to closest official category
            category = map_to_official_category(category)
        
        return {
            "name": extracted.get("name"),
            "contact": extracted.get("contact"),
            "area": extracted.get("area"),
            "category": category,
            "description": extracted.get("description", ""),
            "language": extracted.get("language", "en")
        }
        
    except Exception as e:
        print(f"❌ Media extraction error: {e}")
        import traceback
        traceback.print_exc()
        return {
            "name": None,
            "contact": None,
            "area": None,
            "category": "Miscellaneous",
            "description": "",
            "language": "en"
        }


def map_to_official_category(input_category: str) -> str:
    """Map any category string to one of the 11 official categories"""
    if not input_category:
        return "Miscellaneous"
    
    input_lower = input_category.lower()
    
    # Direct mappings
    category_mappings = {
        # Water related
        "water": "Water & Irrigation",
        "irrigation": "Water & Irrigation",
        "drinking water": "Water & Irrigation",
        "borewell": "Water & Irrigation",
        "tank": "Water & Irrigation",
        "pipeline": "Water & Irrigation",
        
        # Agriculture
        "farming": "Agriculture",
        "crop": "Agriculture",
        "farmer": "Agriculture",
        "agricultural": "Agriculture",
        
        # Health
        "health": "Health & Sanitation",
        "hospital": "Health & Sanitation",
        "medical": "Health & Sanitation",
        "sanitation": "Health & Sanitation",
        "garbage": "Health & Sanitation",
        "drainage": "Health & Sanitation",
        
        # Education
        "school": "Education",
        "college": "Education",
        "educational": "Education",
        
        # Infrastructure
        "road": "Infrastructure & Roads",
        "infrastructure": "Infrastructure & Roads",
        "bridge": "Infrastructure & Roads",
        "street light": "Infrastructure & Roads",
        "construction": "Infrastructure & Roads",
        
        # Law & Order
        "police": "Law & Order",
        "crime": "Law & Order",
        "safety": "Law & Order",
        "security": "Law & Order",
        
        # Welfare
        "pension": "Welfare Schemes",
        "ration": "Welfare Schemes",
        "welfare": "Welfare Schemes",
        "scheme": "Welfare Schemes",
        "housing": "Welfare Schemes",
        
        # Electricity
        "power": "Electricity",
        "current": "Electricity",
        "transformer": "Electricity",
        "electric": "Electricity",
        
        # Environment
        "forest": "Forests & Environment",
        "environment": "Forests & Environment",
        "pollution": "Forests & Environment",
        "tree": "Forests & Environment",
        
        # Finance
        "tax": "Finance & Taxation",
        "finance": "Finance & Taxation",
        
        # Urban/Rural
        "urban": "Urban & Rural Development",
        "rural": "Urban & Rural Development",
        "development": "Urban & Rural Development",
        "municipal": "Urban & Rural Development",
        "panchayat": "Urban & Rural Development",
    }
    
    for key, official in category_mappings.items():
        if key in input_lower:
            return official
    
    # Check if already an official category
    for official in OFFICIAL_CATEGORIES:
        if official.lower() == input_lower:
            return official
    
    return "Miscellaneous"


# ==============================================================================
# TEXT-BASED GRIEVANCE EXTRACTION (For WhatsApp text messages)
# ==============================================================================

async def extract_grievance_from_text(text: str, sender_name: str, sender_phone: str) -> Dict[str, Any]:
    """
    Extract structured grievance data from unstructured text.
    CRITICAL: Category must be in ENGLISH.
    """
    detected_lang = detect_language(text)
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"text-extract-{uuid.uuid4()}",
            system_message="""You are an AI assistant for a government grievance system in India.
Extract structured information from user messages in any Indian language.

CRITICAL RULES:
1. Category MUST be in ENGLISH from this exact list:
   - Water & Irrigation, Agriculture, Forests & Environment, Health & Sanitation,
   - Education, Infrastructure & Roads, Law & Order, Welfare Schemes,
   - Finance & Taxation, Urban & Rural Development, Electricity, Miscellaneous

2. Description should be the English translation/summary of the issue
3. Preserve original area names (don't translate village/town names)"""
        ).with_model("gemini", "gemini-2.0-flash")
        
        prompt = f"""Extract grievance from this message:

MESSAGE: "{text}"
SENDER: {sender_name}
PHONE: {sender_phone}

Return JSON only:
{{"name": "name or null", "area": "location or null", "category": "ENGLISH category", "description": "issue in ENGLISH", "has_complete_info": true/false}}"""
        
        result = await chat.send_message(UserMessage(text=prompt))
        clean_result = result.replace('```json', '').replace('```', '').strip()
        extracted = json.loads(clean_result)
        
        # Normalize category
        category = extracted.get("category", "Miscellaneous")
        if category not in OFFICIAL_CATEGORIES:
            category = map_to_official_category(category)
        
        return {
            "name": extracted.get("name") or sender_name,
            "contact": sender_phone,
            "area": extracted.get("area"),
            "category": category,
            "description": extracted.get("description", text),
            "language": detected_lang,
            "has_complete_info": extracted.get("has_complete_info", False)
        }
        
    except Exception as e:
        print(f"⚠️ Text extraction failed: {e}")
        category, priority, _ = categorize_text(text)
        return {
            "name": sender_name,
            "contact": sender_phone,
            "area": None,
            "category": category,
            "description": text,
            "language": detected_lang,
            "has_complete_info": False
        }


# ==============================================================================
# AUDIO TRANSCRIPTION - Emergent Integrations Wrapper
# ==============================================================================

async def transcribe_audio(audio_binary: bytes, content_type: str = "audio/ogg") -> str:
    """
    Robust transcription using Emergent Integrations Wrapper
    Handles OGG/OPUS to MP3 conversion for Whisper compatibility
    """
    try:
        # Determine original format
        original_ext = 'ogg'
        if 'mp3' in content_type or 'mpeg' in content_type:
            original_ext = 'mp3'
        elif 'wav' in content_type:
            original_ext = 'wav'
        elif 'amr' in content_type:
            original_ext = 'amr'
        
        # Create temp file with original extension
        temp_id = str(uuid.uuid4())
        original_path = f"/tmp/audio_{temp_id}.{original_ext}"
        
        with open(original_path, 'wb') as temp_audio:
            temp_audio.write(audio_binary)
        
        print(f"🎤 Audio saved: {original_path}, size: {len(audio_binary)} bytes")
        
        # Convert to MP3 if needed (Whisper doesn't support OGG)
        transcribe_path = original_path
        if original_ext in ['ogg', 'opus', 'amr']:
            mp3_path = f"/tmp/audio_{temp_id}.mp3"
            try:
                result = subprocess.run([
                    'ffmpeg', '-i', original_path,
                    '-acodec', 'libmp3lame', '-ar', '16000', '-ac', '1',
                    '-y', mp3_path
                ], capture_output=True, text=True, timeout=30)
                
                if result.returncode == 0:
                    transcribe_path = mp3_path
                    print(f"🔄 Converted to MP3: {mp3_path}")
                else:
                    print(f"⚠️ FFmpeg conversion failed: {result.stderr}")
            except Exception as conv_error:
                print(f"⚠️ FFmpeg error: {conv_error}")
        
        # Use Emergent Wrapper for Whisper
        transcriber = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
        
        with open(transcribe_path, 'rb') as audio_file:
            response = await transcriber.transcribe(
                file=audio_file,
                model="whisper-1",
                response_format="json"
            )
        
        # Extract text
        transcript = response.text if hasattr(response, 'text') else str(response)
        transcript = transcript.strip()
        
        print(f"📝 Transcription result: {transcript[:100] if transcript else 'EMPTY'}...")
        
        # Clean up
        try:
            os.remove(original_path)
            if transcribe_path != original_path:
                os.remove(transcribe_path)
        except:
            pass
        
        return transcript
        
    except Exception as e:
        print(f"❌ Transcription Critical Error: {e}")
        import traceback
        traceback.print_exc()
        return ""


# ==============================================================================
# LEGACY FUNCTIONS (For backward compatibility)
# ==============================================================================

SCHEME_DATA = {
    "rajiv yuva kiranam": "Rajiv Yuva Kiranam is a Youth Skill Development scheme for ages 18-35 in Telangana. It provides free training in various skills along with a stipend.",
    "rythu bandhu": "Rythu Bandhu is a farmer investment support scheme providing Rs. 10,000 per acre per year to land-owning farmers in Telangana.",
    "asara pension": "Asara Pension scheme provides monthly pension of Rs. 2,016 to eligible beneficiaries including elderly, widows, disabled persons, and weavers.",
    "kalyana lakshmi": "Kalyana Lakshmi provides Rs. 1,00,116 for marriage of girls from economically weaker sections.",
    "aarogyasri": "Aarogyasri Health Insurance provides free treatment up to Rs. 5 lakhs per family per year for BPL families.",
}


def categorize_text(text: str) -> tuple:
    """
    Categorize text using 11-Sector Framework
    Returns: (category, priority_level, deadline_hours)
    """
    text_lower = text.lower()
    
    # Emergency keywords - CRITICAL priority
    critical_keywords = ["fire", "accident", "current", "open wire", "shock", "danger", "emergency", "death", "collapse", "అత్యవసరం", "ప్రమాదం", "आग", "दुर्घटना"]
    if any(k in text_lower for k in critical_keywords):
        return ("Health & Sanitation", "CRITICAL", 4)
    
    # Category keywords
    CATEGORY_KEYWORDS = {
        "Water & Irrigation": ["water", "irrigation", "canal", "borewell", "tank", "drinking", "pipeline", "tap", "నీరు", "నీటి", "पानी", "जल"],
        "Agriculture": ["crop", "seed", "farmer", "fertilizer", "msp", "drought", "harvest", "రైతు", "పంట", "किसान", "फसल"],
        "Health & Sanitation": ["hospital", "doctor", "medicine", "dengue", "garbage", "sanitation", "ఆసుపత్రి", "अस्पताल"],
        "Education": ["school", "college", "teacher", "student", "exam", "scholarship", "పాఠశాల", "स्कूल"],
        "Infrastructure & Roads": ["road", "pothole", "bridge", "street light", "construction", "రోడ్డు", "सड़क"],
        "Law & Order": ["police", "theft", "crime", "safety", "harassment", "పోలీసు", "पुलिस"],
        "Welfare Schemes": ["pension", "ration", "housing", "scheme", "aadhaar", "పింఛను", "రేషన్", "पेंशन", "राशन"],
        "Electricity": ["electricity", "power", "current", "wire", "transformer", "విద్యుత్", "కరెంట్", "बिजली"],
    }
    
    # Detect category
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


def analyze_interaction(text: str, sender_phone: str) -> dict:
    """
    Analyze text to determine if it's a QUERY or GRIEVANCE
    """
    try:
        text_lower = text.lower()
        
        # Quick Keyword Check for Schemes (RAG-Lite)
        for scheme_key, scheme_info in SCHEME_DATA.items():
            if scheme_key.replace(" ", "") in text_lower.replace(" ", "") or scheme_key in text_lower:
                return {
                    "type": "QUERY",
                    "response": scheme_info + "\n\nWould you like me to register any specific issue?",
                    "data": {
                        "category": "Welfare Schemes",
                        "priority_level": "LOW"
                    }
                }
        
        # Use categorization logic
        category, priority, deadline = categorize_text(text)
        
        return {
            "type": "GRIEVANCE",
            "response": f"I've noted your concern about {category}. This has been marked as {priority} priority.",
            "data": {
                "category": category,
                "priority_level": priority,
                "description": text,
                "status": "pending",
                "citizen_phone": sender_phone
            }
        }
        
    except Exception as e:
        print(f"❌ AI Analysis Error: {e}")
        return {
            "type": "QUERY",
            "response": "I understand you have a concern. Could you please provide more details?",
            "data": {"category": "Miscellaneous", "priority_level": "MEDIUM"}
        }


# ==============================================================================
# API ENDPOINTS
# ==============================================================================

class AIAnalysisRequest(BaseModel):
    text: str
    analysis_type: str

class AIGenerateRequest(BaseModel):
    prompt: str
    context: Optional[str] = None

class GrievanceAnalysis(BaseModel):
    text: str

class LanguageDetectRequest(BaseModel):
    text: str

class TranslateRequest(BaseModel):
    text: str
    target_lang: str


@router.post("/detect_language")
def detect_language_endpoint(request: LanguageDetectRequest):
    """Detect language of input text"""
    lang = detect_language(request.text)
    return {"language": lang, "text": request.text}


@router.post("/translate")
async def translate_endpoint(request: TranslateRequest):
    """Translate text to target language"""
    translated = await translate_text(request.text, request.target_lang)
    return {"original": request.text, "translated": translated, "target_lang": request.target_lang}


@router.post("/analyze_priority")
def analyze_priority_endpoint(request: GrievanceAnalysis):
    """11-Sector Governance Framework Priority Analysis"""
    category, priority, deadline = categorize_text(request.text)
    
    return {
        "priority_level": priority,
        "category": category,
        "deadline_hours": deadline,
        "reason": f"Classified under {category}"
    }


@router.post("/extract_from_media")
async def extract_from_media_endpoint(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """Extract grievance data from uploaded PDF or image"""
    try:
        content = await file.read()
        media_type = file.content_type or "application/octet-stream"
        
        extracted = await extract_grievance_from_media(content, media_type)
        
        return {
            "success": True,
            "data": extracted
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcribe")
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """Transcribe audio file using Emergent Whisper"""
    try:
        content = await file.read()
        content_type = file.content_type or "audio/ogg"
        
        transcript = await transcribe_audio(content, content_type)
        
        if transcript:
            # Also detect language
            lang = detect_language(transcript)
            return {"success": True, "text": transcript, "language": lang}
        else:
            raise HTTPException(status_code=500, detail="Transcription failed - empty result")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-grievance")
async def analyze_grievance(
    data: AIAnalysisRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """AI-powered grievance analysis using Gemini"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"grievance-{current_user.user_id}",
            system_message="You are an AI assistant helping analyze constituent grievances for Indian legislators. Provide priority scores (1-10) and actionable resolution steps."
        ).with_model("gemini", "gemini-2.0-flash")
        
        analysis_prompt = f"""Analyze this constituent grievance and provide:
1. Priority score (1-10, where 10 is most urgent)
2. Issue category (from 11 official categories)
3. Suggested resolution steps (2-3 actionable items)

Grievance: {data.text}

Respond in JSON format with keys: priority, category, resolution_steps"""
        
        user_message = UserMessage(text=analysis_prompt)
        response = await chat.send_message(user_message)
        
        return {"analysis": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/generate-response")
async def generate_response(
    data: AIGenerateRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Generate AI response for drafting communications"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"response-{current_user.user_id}",
            system_message="You are an AI assistant helping Indian legislators draft professional responses. Be formal, empathetic, and solution-oriented."
        ).with_model("gemini", "gemini-2.0-flash")
        
        context_info = f"\nContext: {data.context}" if data.context else ""
        
        generate_prompt = f"""Generate a professional response for this communication:

Topic: {data.prompt}{context_info}

Provide a well-structured, formal response suitable for official communication."""
        
        user_message = UserMessage(text=generate_prompt)
        response = await chat.send_message(user_message)
        
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/draft-broadcast")
async def draft_broadcast(
    data: AIGenerateRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """Generate AI draft for social media broadcast"""
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"broadcast-{current_user.user_id}",
            system_message="You are a social media content creator for an Indian politician. Create engaging, professional posts."
        ).with_model("gemini", "gemini-2.0-flash")
        
        platform_context = data.context if data.context else "general social media"
        
        broadcast_prompt = f"""Create a social media post for {platform_context}:

Topic: {data.prompt}

Requirements:
- Engaging and accessible language
- Professional tone
- Include relevant hashtags"""
        
        user_message = UserMessage(text=broadcast_prompt)
        response = await chat.send_message(user_message)
        
        return {"draft": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
