"""
YOU - Governance ERP AI Routes
OSD PERSONA UPDATE: Intent Classification + Native Language Resolution
Updated: 2026-02-06
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional, Dict, Any
from auth import get_current_user, TokenData
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContent
from emergentintegrations.llm.openai import OpenAISpeechToText
import os
import uuid
import json
import base64
import subprocess

router = APIRouter()

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# ==============================================================================
# 11 OFFICIAL CATEGORIES (ENGLISH ONLY)
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
# LANGUAGE DETECTION (Frugal - Unicode-based, no LLM)
# ==============================================================================
LANGUAGE_SCRIPTS = {
    'te': (0x0C00, 0x0C7F),  # Telugu
    'hi': (0x0900, 0x097F),  # Hindi/Devanagari
    'ta': (0x0B80, 0x0BFF),  # Tamil
    'kn': (0x0C80, 0x0CFF),  # Kannada
    'ml': (0x0D00, 0x0D7F),  # Malayalam
    'bn': (0x0980, 0x09FF),  # Bengali
}

def detect_language(text: str) -> str:
    """Detect language using Unicode script ranges (no LLM = frugal)"""
    if not text:
        return 'en'
    
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
    
    max_lang = max(script_counts, key=script_counts.get)
    if script_counts[max_lang] > total_alpha * 0.2:
        return max_lang
    
    return 'en'


# ==============================================================================
# THE "OSD BRAIN" - INTENT CLASSIFICATION
# ==============================================================================

async def analyze_incoming_message(text: str, sender_name: str = "Citizen", sender_phone: str = "") -> Dict[str, Any]:
    """
    The Core Intelligence - OSD Persona with STRICT Language Control.
    Fixes: No foreign languages (French/Spanish), Medical domain knowledge, Hinglish mirroring.
    """
    
    # First detect language (frugal, no LLM)
    detected_lang = detect_language(text)
    
    system_prompt = """You are the Officer on Special Duty (OSD) for a prominent Indian political leader.
Your role is to assist citizens with EMPATHY, SPEED, and ACCURACY.

*** CRITICAL LANGUAGE RULES - STRICTLY FOLLOW ***
1. **MIRROR THE EXACT SCRIPT**: 
   - If user writes Hindi in English script ("Tabiyat kharab hai"), you MUST reply in Hindi using English script ("Kripya details dein, hum madad karenge")
   - If user writes in Telugu script (తెలుగు), reply in Telugu script
   - If user writes in Hindi Devanagari (हिंदी), reply in Devanagari
   - If user writes in English, reply in English

2. **ABSOLUTELY NO FOREIGN LANGUAGES**: 
   - NEVER reply in French, Spanish, German, Portuguese, or any non-Indian language
   - ONLY use: English, Hindi (Devanagari), Hindi (Roman/Hinglish), Telugu, Tamil, Kannada, Malayalam, Bengali
   - If unsure, default to English or Hinglish

3. **CONSISTENCY**: Never switch languages mid-conversation unless the user switches first

*** DOMAIN KNOWLEDGE (GOVERNANCE & MEDICAL) ***
**Medical Emergencies:**
- For ANY medical help request, IMMEDIATELY suggest: "108 Ambulance" for emergencies
- Mention "Aarogyasri" health scheme for hospital bills assistance
- Mention "CM Relief Fund" for financial help with treatment
- Direct to nearest PHC (Primary Health Centre) or Government Hospital
- For hospital admission issues: "Aap District Collector office mein complaint kar sakte hain, ya Chief Medical Officer ko contact karein"

**Government Schemes (Know these):**
- Aarogyasri: Free healthcare up to Rs 5 lakh for BPL families
- Rythu Bandhu: Rs 10,000/acre to farmers
- Asara Pension: Monthly pension for elderly/disabled
- PM Kisan: Rs 6,000/year to farmers
- Ration Card: Apply at MeeSeva/CSC centers
- Housing: PMAY, Indiramma, Double Bedroom schemes

**Civic Issues:** Water, Drainage, Roads, Streetlights, Electricity, Sanitation

*** INTENT CLASSIFICATION ***
1. 'CHAT': Greetings, small talk, thank you
2. 'GRIEVANCE': Specific complaints (Roads damaged, Water not coming, Pension not received, Hospital refusing treatment)
3. 'STATUS': Asking "What happened to my complaint?"
4. 'FEEDBACK': Ratings (1-5) or appreciation
5. 'GENERAL_QUERY': Asking for information about schemes, hospitals, jobs, processes

*** OUTPUT FORMAT (JSON only, no markdown) ***
{
    "intent": "CHAT" | "GRIEVANCE" | "STATUS" | "FEEDBACK" | "GENERAL_QUERY",
    "detected_language": "en/te/hi/hinglish/ta/kn/ml/bn",
    "reply": "Response in EXACT SAME language/script as user input - NO FRENCH/SPANISH/etc",
    "grievance_data": {
        "name": "extracted or null",
        "area": "extracted or null", 
        "category": "ENGLISH category from official list",
        "description": "issue summary in English"
    }
}

REMEMBER: If user writes "Mera beta ka ilaaz..." you reply "Aapki madad ke liye..." - SAME SCRIPT!"""

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"osd-brain-{uuid.uuid4()}",
            system_message=system_prompt
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""Analyze this message from {sender_name}:

MESSAGE: "{text}"

CRITICAL INSTRUCTIONS:
1. Detect if this is Hinglish (Hindi in English letters like "Mera beta ka ilaaz kaarana hai")
2. If Hinglish detected, you MUST reply in Hinglish (Hindi words in English letters)
3. For medical issues, mention 108 ambulance, Aarogyasri scheme, CMO office
4. ABSOLUTELY DO NOT reply in French, Spanish, or any non-Indian language
5. If the message is about hospital refusing treatment, this is a GRIEVANCE about Health

Classify intent and respond in the EXACT SAME language/script as the user."""

        result = await chat.send_message(UserMessage(text=prompt))
        clean_result = result.replace('```json', '').replace('```', '').strip()
        parsed = json.loads(clean_result)
        
        # Safety check - ensure no foreign language in reply
        reply = parsed.get('reply', '')
        foreign_indicators = ['je ', 'j\'ai', 'votre', 'nous', 'merci', 'bonjour', 'réclamation', 'gracias', 'hola', 'danke', 'bitte']
        if any(indicator in reply.lower() for indicator in foreign_indicators):
            # Fallback to safe Hinglish response
            if 'medical' in text.lower() or 'hospital' in text.lower() or 'doctor' in text.lower() or 'ilaaz' in text.lower() or 'bimar' in text.lower():
                parsed['reply'] = "Aapki pareshani samajh mein aayi. Medical emergency ke liye 108 ambulance call karein. Hospital mein problem ho toh District Collector office mein complaint karein. Aarogyasri scheme se free treatment mil sakta hai. Hum aapki madad zaroor karenge."
            else:
                parsed['reply'] = "Aapki baat note kar li hai. Jald se jald aapko update milega. Kripya thoda intezaar karein."
        
        parsed['detected_language'] = parsed.get('detected_language', detected_lang)
        
        return parsed
        
    except Exception as e:
        print(f"❌ OSD Brain Error: {e}")
        return {
            "intent": "CHAT",
            "detected_language": detected_lang,
            "reply": "Main aapki madad ke liye yahan hoon. Kaise help kar sakta hoon?",
            "grievance_data": None
        }


# ==============================================================================
# TRANSLATION SERVICE (For resolution notifications)
# ==============================================================================

async def translate_text(text: str, target_lang: str) -> str:
    """Translate admin messages (like 'Resolved') into user's native language"""
    if target_lang == 'en':
        return text
    
    lang_names = {
        'te': 'Telugu', 'hi': 'Hindi', 'ta': 'Tamil',
        'kn': 'Kannada', 'ml': 'Malayalam', 'bn': 'Bengali'
    }
    target_name = lang_names.get(target_lang, 'the local language')
    
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"translate-{uuid.uuid4()}",
            system_message=f"You are a professional translator. Translate the given text to {target_name}. Keep it formal and respectful. Only return the translated text."
        ).with_model("gemini", "gemini-2.0-flash")
        
        result = await chat.send_message(UserMessage(text=f"Translate: {text}"))
        return result.strip()
    except Exception as e:
        print(f"⚠️ Translation failed: {e}")
        return text


# ==============================================================================
# MEDIA EXTRACTION (PDF/Image with GPT-4o Vision)
# ==============================================================================

async def extract_grievance_from_media(media_data: bytes, media_type: str) -> Dict[str, Any]:
    """
    HIGH-PRECISION "Deep OCR" extraction for PDF/Image.
    Handles mixed languages (Hindi name, English description) and normalizes ALL fields to English.
    """
    try:
        media_base64 = base64.b64encode(media_data).decode('utf-8')
        
        if 'pdf' in media_type.lower():
            content_type = "application/pdf"
        elif 'png' in media_type.lower():
            content_type = "image/png"
        else:
            content_type = "image/jpeg"
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"deep-ocr-{uuid.uuid4()}",
            system_message="""You are an expert OCR system for government grievance documents in India.
Your task is DEEP OCR with ENGLISH NORMALIZATION.

CRITICAL INSTRUCTIONS:
1. The document may contain MIXED LANGUAGES (Hindi, Telugu, Tamil, English mixed together)
2. You MUST identify and extract ALL entities regardless of script
3. ALL OUTPUT FIELDS MUST BE IN ENGLISH - transliterate/translate everything

ENTITY EXTRACTION RULES:
- NAME: Look for "Name", "Applicant", "नाम", "పేరు", "பெயர்" etc. TRANSLITERATE to English (e.g., "राम कुमार" → "Ram Kumar")
- AREA: Look for "Mandal", "Village", "Ward", "मंडल", "गांव", "మండలం", "గ్రామం". TRANSLITERATE accurately (e.g., "అల్వాల్" → "Alwal")
- CONTACT: Extract any 10-digit phone numbers
- CATEGORY: Map to official English categories only
- DESCRIPTION: Read entire content in any language, summarize in CLEAR ENGLISH

OFFICIAL CATEGORIES (pick one):
Water & Irrigation, Agriculture, Health & Sanitation, Education, Infrastructure & Roads, 
Law & Order, Welfare Schemes, Electricity, Forests & Environment, Finance & Taxation, 
Urban & Rural Development, Miscellaneous"""
        ).with_model("openai", "gpt-4o")
        
        prompt = """Perform DEEP OCR on this document/image.

EXTRACT and NORMALIZE TO ENGLISH:
1. Name (transliterate from any script to English)
2. Contact Number (10 digits if found)
3. Area/Location (transliterate Mandal/Village/Ward names to English)
4. Issue Category (MUST be from official English list)
5. Issue Description (translate/summarize in English)
6. Original Document Language

Return JSON only (no markdown):
{
    "name": "English transliterated name or null",
    "contact": "phone number or null",
    "area": "English transliterated area name or null",
    "category": "Official English category",
    "description": "English description/summary",
    "language": "original language code (en/te/hi/ta)"
}"""
        
        msg = UserMessage(text=prompt, file_contents=[FileContent(content_type=content_type, file_content_base64=media_base64)])
        result = await chat.send_message(msg)
        
        clean_result = result.replace('```json', '').replace('```', '').strip()
        extracted = json.loads(clean_result)
        
        # Ensure category is from official list
        if extracted.get('category') not in OFFICIAL_CATEGORIES:
            extracted['category'] = map_to_official_category(extracted.get('category', ''))
        
        return extracted
        
    except Exception as e:
        print(f"❌ Deep OCR extraction error: {e}")
        return None


# ==============================================================================
# AUDIO TRANSCRIPTION
# ==============================================================================

async def transcribe_audio(audio_binary: bytes, content_type: str = "audio/ogg") -> str:
    """
    Transcribe audio using Whisper via Emergent wrapper.
    Handles OGG/OPUS to MP3 conversion for WhatsApp voice notes.
    """
    try:
        if not audio_binary or len(audio_binary) < 100:
            print(f"❌ Audio data too small or empty: {len(audio_binary) if audio_binary else 0} bytes")
            return ""
        
        temp_id = str(uuid.uuid4())
        
        # Determine original format
        original_ext = 'ogg'
        if 'mp3' in content_type or 'mpeg' in content_type:
            original_ext = 'mp3'
        elif 'wav' in content_type:
            original_ext = 'wav'
        elif 'amr' in content_type:
            original_ext = 'amr'
        elif 'opus' in content_type:
            original_ext = 'opus'
        
        original_path = f"/tmp/audio_{temp_id}.{original_ext}"
        
        # Save audio to temp file
        with open(original_path, 'wb') as f:
            f.write(audio_binary)
        
        file_size = os.path.getsize(original_path)
        print(f"🎤 Audio saved: {original_path}, size: {file_size} bytes, type: {content_type}")
        
        if file_size < 100:
            print(f"❌ Audio file too small after save: {file_size} bytes")
            os.remove(original_path)
            return ""
        
        # Convert to MP3 if needed (Whisper doesn't support OGG/OPUS well)
        transcribe_path = original_path
        if original_ext in ['ogg', 'opus', 'amr']:
            mp3_path = f"/tmp/audio_{temp_id}.mp3"
            try:
                print(f"🔄 Converting {original_ext} to MP3...")
                result = subprocess.run(
                    ['ffmpeg', '-i', original_path, '-acodec', 'libmp3lame', '-ar', '16000', '-ac', '1', '-b:a', '64k', '-y', mp3_path],
                    capture_output=True, text=True, timeout=60
                )
                
                if result.returncode == 0 and os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 100:
                    transcribe_path = mp3_path
                    print(f"✅ Converted to MP3: {mp3_path}, size: {os.path.getsize(mp3_path)} bytes")
                else:
                    print(f"⚠️ FFmpeg conversion failed or output too small. stderr: {result.stderr[:200] if result.stderr else 'none'}")
                    # Try with original file anyway
            except subprocess.TimeoutExpired:
                print(f"⚠️ FFmpeg conversion timed out")
            except Exception as conv_error:
                print(f"⚠️ FFmpeg error: {conv_error}")
        
        # Transcribe using Emergent Wrapper
        print(f"🎯 Transcribing: {transcribe_path}")
        transcriber = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
        
        with open(transcribe_path, 'rb') as audio_file:
            response = await transcriber.transcribe(
                file=audio_file,
                model="whisper-1",
                response_format="json"
            )
        
        # Extract text from response
        if hasattr(response, 'text'):
            transcript = response.text
        elif isinstance(response, dict):
            transcript = response.get('text', str(response))
        else:
            transcript = str(response)
        
        transcript = transcript.strip()
        print(f"📝 Transcription result: '{transcript[:100]}...' " if len(transcript) > 100 else f"📝 Transcription result: '{transcript}'")
        
        # Cleanup temp files
        try:
            if os.path.exists(original_path):
                os.remove(original_path)
            if transcribe_path != original_path and os.path.exists(transcribe_path):
                os.remove(transcribe_path)
        except Exception as cleanup_error:
            print(f"⚠️ Cleanup error: {cleanup_error}")
        
        return transcript
        
    except Exception as e:
        print(f"❌ Transcription Critical Error: {e}")
        import traceback
        traceback.print_exc()
        return ""


# ==============================================================================
# CATEGORY MAPPING
# ==============================================================================

def map_to_official_category(input_category: str) -> str:
    """Map any category string to one of the 11 official English categories"""
    if not input_category:
        return "Miscellaneous"
    
    input_lower = input_category.lower()
    
    mappings = {
        "water": "Water & Irrigation", "irrigation": "Water & Irrigation",
        "agriculture": "Agriculture", "farming": "Agriculture",
        "health": "Health & Sanitation", "hospital": "Health & Sanitation", "sanitation": "Health & Sanitation",
        "education": "Education", "school": "Education",
        "road": "Infrastructure & Roads", "infrastructure": "Infrastructure & Roads", "bridge": "Infrastructure & Roads",
        "police": "Law & Order", "crime": "Law & Order", "safety": "Law & Order",
        "pension": "Welfare Schemes", "ration": "Welfare Schemes", "welfare": "Welfare Schemes",
        "electricity": "Electricity", "power": "Electricity", "current": "Electricity",
        "forest": "Forests & Environment", "environment": "Forests & Environment",
        "tax": "Finance & Taxation",
        "urban": "Urban & Rural Development", "rural": "Urban & Rural Development",
    }
    
    for key, official in mappings.items():
        if key in input_lower:
            return official
    
    if input_category in OFFICIAL_CATEGORIES:
        return input_category
    
    return "Miscellaneous"


def categorize_text(text: str) -> tuple:
    """Quick categorization based on keywords"""
    text_lower = text.lower()
    
    critical_keywords = ["fire", "accident", "emergency", "death", "collapse", "danger"]
    if any(k in text_lower for k in critical_keywords):
        return ("Health & Sanitation", "CRITICAL", 4)
    
    category_keywords = {
        "Water & Irrigation": ["water", "borewell", "tank", "pipeline", "నీరు", "पानी"],
        "Agriculture": ["crop", "farmer", "farming", "రైతు", "किसान"],
        "Health & Sanitation": ["hospital", "doctor", "garbage", "ఆసుపత్రి", "अस्पताल"],
        "Education": ["school", "college", "teacher", "పాఠశాల", "स्कूल"],
        "Infrastructure & Roads": ["road", "pothole", "bridge", "రోడ్డు", "सड़क"],
        "Law & Order": ["police", "theft", "crime", "పోలీసు", "पुलिस"],
        "Welfare Schemes": ["pension", "ration", "housing", "పింఛను", "पेंशन"],
        "Electricity": ["electricity", "power", "transformer", "విద్యుత్", "बिजली"],
    }
    
    for category, keywords in category_keywords.items():
        if any(k in text_lower for k in keywords):
            if category in ["Health & Sanitation", "Law & Order", "Electricity"]:
                return (category, "CRITICAL", 4)
            elif category in ["Water & Irrigation", "Infrastructure & Roads"]:
                return (category, "HIGH", 24)
            else:
                return (category, "MEDIUM", 72)
    
    return ("Miscellaneous", "LOW", 336)


# ==============================================================================
# API ENDPOINTS
# ==============================================================================

class LanguageDetectRequest(BaseModel):
    text: str

class TranslateRequest(BaseModel):
    text: str
    target_lang: str

class AnalyzeRequest(BaseModel):
    text: str
    sender_name: Optional[str] = "Citizen"
    sender_phone: Optional[str] = ""

class GrievanceAnalysis(BaseModel):
    text: str


@router.post("/detect_language")
def detect_language_endpoint(request: LanguageDetectRequest):
    """Detect language of input text"""
    return {"language": detect_language(request.text), "text": request.text}


@router.post("/translate")
async def translate_endpoint(request: TranslateRequest):
    """Translate text to target language"""
    translated = await translate_text(request.text, request.target_lang)
    return {"original": request.text, "translated": translated, "target_lang": request.target_lang}


@router.post("/analyze_intent")
async def analyze_intent_endpoint(request: AnalyzeRequest):
    """Analyze message intent using OSD Brain"""
    result = await analyze_incoming_message(request.text, request.sender_name, request.sender_phone)
    return result


@router.post("/analyze_priority")
def analyze_priority_endpoint(request: GrievanceAnalysis):
    """Quick priority analysis"""
    category, priority, deadline = categorize_text(request.text)
    return {"priority_level": priority, "category": category, "deadline_hours": deadline}


@router.post("/extract_from_media")
async def extract_from_media_endpoint(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """Extract grievance data from PDF or image"""
    try:
        content = await file.read()
        media_type = file.content_type or "application/octet-stream"
        extracted = await extract_grievance_from_media(content, media_type)
        return {"success": True, "data": extracted}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcribe")
async def transcribe_endpoint(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """Transcribe audio file"""
    try:
        content = await file.read()
        transcript = await transcribe_audio(content, file.content_type or "audio/ogg")
        if transcript:
            return {"success": True, "text": transcript, "language": detect_language(transcript)}
        raise HTTPException(status_code=500, detail="Transcription failed")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
