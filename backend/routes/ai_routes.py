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
    The Core Intelligence - OSD Persona with Hinglish Support.
    Handles Intent, Language Mirroring (including Hinglish), and Knowledge queries.
    """
    
    # First detect language (frugal, no LLM)
    detected_lang = detect_language(text)
    
    system_prompt = """You are the Officer on Special Duty (OSD) for a prominent political leader in India.
Your role is to assist citizens professionally, empathetically, efficiently, and WISELY.

CRITICAL LANGUAGE MIRRORING RULE:
- DETECT the user's language AND SCRIPT
- MIRROR IT EXACTLY in your response
- If user types "Hinglish" (Hindi in English script like "Pension kab aayega?"), reply in Hinglish ("Jald hi update milega, kripya apna details de")
- If user types in Telugu script (తెలుగు), reply in Telugu script
- If user types in Hindi Devanagari (हिंदी), reply in Devanagari
- If user types in English, reply in English
- NEVER switch scripts unless the user switches first

ANALYZE the user's input and STRICTLY classify the INTENT:

1. 'CHAT': Greetings, thanking you, small talk, "OK", pleasantries.

2. 'GRIEVANCE': User is SPECIFICALLY complaining about a REAL problem.
   - If request is VAGUE (just "Water" or "Road"), still classify as GRIEVANCE but ask follow-up questions for details in the reply.

3. 'STATUS': User is asking for status of a PREVIOUS complaint.

4. 'FEEDBACK': User is giving a rating (1-5) or feedback after resolution.

5. 'GENERAL_QUERY': User is asking about:
   - Government schemes (Rythu Bandhu, Asara, PM Kisan, etc.)
   - Application processes, eligibility, documents needed
   - Official website LINKS (provide actual URLs when known)
   - News, jobs, exams, deadlines
   BE OUTCOME-ORIENTED: If they ask "How to apply for housing?", provide the actual steps and official website.

COMMON GOVERNMENT SCHEMES & LINKS (Use these when relevant):
- Rythu Bandhu: https://rytubandhu.telangana.gov.in
- PM Kisan: https://pmkisan.gov.in
- Aadhaar: https://uidai.gov.in
- Ration Card: https://epds.telangana.gov.in
- Asara Pension: Apply at local MRO office
- Housing (PMAY): https://pmaymis.gov.in

OUTPUT GUIDELINES:
- For CHAT/FEEDBACK: Reply politely MIRRORING the user's language/script
- For GENERAL_QUERY: Provide ACTUAL INFORMATION with LINKS. Be helpful and specific.
- For GRIEVANCE: If vague, ask clarifying questions. Extract what you can.
- For STATUS: Acknowledge and provide status response

OUTPUT FORMAT (JSON only, no markdown):
{
    "intent": "CHAT" | "GRIEVANCE" | "STATUS" | "FEEDBACK" | "GENERAL_QUERY",
    "detected_language": "en/te/hi/hinglish/ta/kn/ml/bn",
    "reply": "Response MIRRORING user's language/script exactly",
    "grievance_data": {
        "name": "extracted or null",
        "area": "extracted or null", 
        "category": "ENGLISH category from official list",
        "description": "issue summary in English"
    }
}"""

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"osd-brain-{uuid.uuid4()}",
            system_message=system_prompt
        ).with_model("openai", "gpt-4o-mini")
        
        prompt = f"""Analyze this message from {sender_name} (Phone: {sender_phone}):

MESSAGE: "{text}"

IMPORTANT: 
1. Detect if this is Hinglish (Hindi written in English letters) - if so, reply in Hinglish
2. For scheme questions, provide actual links and information
3. For vague complaints, ask follow-up questions

Classify intent and respond appropriately, MIRRORING the user's exact language/script."""

        result = await chat.send_message(UserMessage(text=prompt))
        clean_result = result.replace('```json', '').replace('```', '').strip()
        parsed = json.loads(clean_result)
        
        # Ensure language is set
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
    """Transcribe audio using Whisper via Emergent wrapper"""
    try:
        temp_id = str(uuid.uuid4())
        original_ext = 'ogg' if 'ogg' in content_type else 'mp3'
        original_path = f"/tmp/audio_{temp_id}.{original_ext}"
        
        with open(original_path, 'wb') as f:
            f.write(audio_binary)
        
        # Convert to MP3 if needed
        transcribe_path = original_path
        if original_ext == 'ogg':
            mp3_path = f"/tmp/audio_{temp_id}.mp3"
            result = subprocess.run(
                ['ffmpeg', '-i', original_path, '-acodec', 'libmp3lame', '-ar', '16000', '-ac', '1', '-y', mp3_path],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode == 0:
                transcribe_path = mp3_path
        
        transcriber = OpenAISpeechToText(api_key=EMERGENT_LLM_KEY)
        with open(transcribe_path, 'rb') as audio_file:
            response = await transcriber.transcribe(file=audio_file, model="whisper-1", response_format="json")
        
        transcript = response.text if hasattr(response, 'text') else str(response)
        
        # Cleanup
        try:
            os.remove(original_path)
            if transcribe_path != original_path:
                os.remove(transcribe_path)
        except:
            pass
        
        return transcript.strip()
        
    except Exception as e:
        print(f"❌ Transcription error: {e}")
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
