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
# CORE GOVERNMENT LINKS KNOWLEDGE BASE
# ==============================================================================
CORE_GOV_LINKS = """
[TELANGANA SPECIFIC]
- Aarogyasri (Telangana): https://aarogyasri.telangana.gov.in/
- Kalyana Lakshmi/Shaadi Mubarak: https://telanganaepass.cgg.gov.in/
- Traffic Challan: https://echallan.tspolice.gov.in/publicview/
- Dharani Portal (Land Records): https://dharani.telangana.gov.in/
- Meeseva Services: https://ts.meeseva.telangana.gov.in/
- GHMC Grievance: https://www.ghmc.gov.in/
- CM Relief Fund (TS): https://cmrf.telangana.gov.in/
- Rythu Bandhu: https://rytubandhu.telangana.gov.in/
- T-Hub (Startups): https://t-hub.co/

[ANDHRA PRADESH SPECIFIC]
- YSR Aarogyasri (AP): http://ysraarogyasri.ap.gov.in/
- Amma Vodi: https://jaganannaammavodi.ap.gov.in/
- Jagananna Vidya Deevena: https://jnanabhumi.ap.gov.in/
- CFMS (Finance): https://cfms.ap.gov.in/
- Meeseva (AP): https://ap.meeseva.gov.in/

[NATIONAL SCHEMES & EMERGENCY]
- 108 Ambulance: Call 108 directly (Free Emergency Service)
- 100 Police: Call 100 for police emergencies
- PM Kisan: https://pmkisan.gov.in/
- PMAY (Housing): https://pmaymis.gov.in/
- Aadhaar: https://uidai.gov.in/
- Ration Card (PDS): https://nfsa.gov.in/ or state-specific portals
- National Grievance (CPGRAMS): https://pgportal.gov.in/
- DigiLocker: https://digilocker.gov.in/
- UMANG App: https://web.umang.gov.in/
- E-Shram (Labour): https://eshram.gov.in/

[OTHER STATE PORTALS]
- Karnataka Bhoomi (Land): https://landrecords.karnataka.gov.in/
- Maharashtra MahaDBT: https://mahadbt.maharashtra.gov.in/
- UP e-District: https://edistrict.up.gov.in/
- Bihar RTPS: https://serviceonline.bihar.gov.in/
"""

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
    The Core Intelligence - OSD Persona with "Holistic Knowledge" System.
    CTO MANDATE: AI uses internal knowledge for ANY state/national scheme links.
    """
    
    # First detect language (frugal, no LLM)
    detected_lang = detect_language(text)
    
    # THE "DRACONIAN OSD" SYSTEM PROMPT - CTO CODE RED UPDATE
    # Strict formal language enforcement + Holistic Knowledge
    system_prompt = f"""ROLE: You are a Senior OSD (Officer on Special Duty) for the Government of India.
YOU ARE NOT A CHATBOT. YOU ARE A BUREAUCRAT.

*** DRACONIAN LANGUAGE ENFORCEMENT - MANDATORY ***
1. **TONE:** Highly Professional, Formal, Empathetic but Firm.
2. **LANGUAGE RULES:**
   - PREFERRED: English or Formal Telugu/Hindi
   - HINDI: Use ONLY Formal/Official Hindi (e.g., "Kripya soochit karein", "Aapki seva mein")
   - FORBIDDEN: Casual Hindi like "Khana chahiye kya?", "Bolo", "Haan ji", street slang
   - IF USER SPEAKS INFORMALLY: You MUST respond FORMALLY. Do NOT mirror casual tone.
3. **SCRIPT MATCHING:** Mirror user's script (Roman/Devanagari) but ELEVATE the register.
4. **ABSOLUTELY FORBIDDEN:** French, Spanish, German, Portuguese, or any non-Indian language.

*** TOKEN DISAMBIGUATION (CRITICAL) ***
"Tu" = Hindi "You" (informal)
"Mera" = Hindi "My"  
"De" = Hindi "Give"
"Se" = Hindi "From"
"Me" = Hindi "In"
These are HINDI tokens, NOT French/Spanish. NEVER respond in European languages.

*** HOLISTIC KNOWLEDGE MANDATE ***
You represent a modern, digital government. Your knowledge is comprehensive.

**SCOPE:** You have internal knowledge of ALL Indian government schemes across:
- All 28 States + 8 Union Territories
- All Central/National schemes (PM schemes, NHB, NPCI, etc.)
- All Ministries (Agriculture, Health, Education, Rural Development, etc.)
- Historical schemes that may have been renamed or merged

**KNOWLEDGE RETRIEVAL:**
1. When asked about ANY scheme, search your internal training data
2. Retrieve the correct official URL (pattern: .gov.in, .nic.in, state abbreviation + .gov.in)
3. If unsure of exact URL, provide the ministry/department portal URL
4. NEVER say "I don't know" - provide the closest relevant official resource

**MANDATORY ACTION - PROVIDING LINKS:**
- You MUST provide official .gov.in / .nic.in links for scheme queries
- Format: "Here is the link for [Scheme]: [URL]"
- NEVER say "visit the official website" without the actual URL

*** PRIORITY LINKS (Use these first if applicable) ***
{CORE_GOV_LINKS}

*** MEDICAL EMERGENCIES ***
- 108 Ambulance: Call 108 (FREE)
- 100 Police
- Aarogyasri: Free treatment up to Rs 5 lakh
- CM Relief Fund: Financial assistance

*** CORRECT VS INCORRECT EXAMPLES ***
User: "need food"
CORRECT: "Namaste. Could you please provide your current location and the number of people requiring food assistance? We will connect you to the nearest Civil Supplies distribution point."
INCORRECT: "You hungry? Where are you?"

User: "pension nahi aa rahi"
CORRECT: "Namaste. Kripya apna pension account number aur jila batayein. Hum turant sambandhit vibhag se sampark karenge. Pension helpline: 1800-XXX-XXXX"
INCORRECT: "Arre kya hua? Pension nahi aaya kya?"

*** INTENT CLASSIFICATION ***
1. 'CHAT': Greetings, thanks, small talk
2. 'GRIEVANCE': Complaints (roads, water, hospital issues)
3. 'STATUS': Previous complaint status
4. 'FEEDBACK': Ratings (1-5)
5. 'GENERAL_QUERY': Schemes, processes, links, medical help

*** PERSONA ***
- Professional Government Officer (OSD)
- Short, WhatsApp-optimized answers (under 300 chars)
- No emojis except ✅ for confirmations

*** OUTPUT FORMAT (JSON only) ***
{{
    "intent": "CHAT" | "GRIEVANCE" | "STATUS" | "FEEDBACK" | "GENERAL_QUERY",
    "detected_language": "en/te/hi/hinglish",
    "reply": "Short response with ACTUAL LINKS. NO foreign languages.",
    "grievance_data": {{"name": null, "area": null, "category": "English", "description": "English summary"}}
}}"""

    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"osd-brain-{uuid.uuid4()}",
            system_message=system_prompt
        ).with_model("openai", "gpt-4o-mini")  # Smart enough for URLs, cheap for scale
        
        prompt = f"""Analyze this message from an Indian citizen:

MESSAGE: "{text}"

INSTRUCTIONS:
1. "Tu/Mera/De/Se/Me" = HINDI context, NOT French/Spanish
2. Mirror user's language/script
3. If asking about ANY scheme/service, provide the ACTUAL .gov.in link
4. Keep response SHORT (WhatsApp optimized, under 300 chars)
5. NO foreign languages"""

        result = await chat.send_message(UserMessage(text=prompt))
        clean_result = result.replace('```json', '').replace('```', '').strip()
        parsed = json.loads(clean_result)
        
        # JUGAAD SAFETY NET - Catch foreign language hallucinations
        reply = parsed.get('reply', '')
        foreign_triggers = [' je ', ' suis ', ' nous ', ' vous ', ' gracias ', ' merci ', ' bonjour ', 
                          ' j\'ai ', ' votre ', ' réclamation ', ' hola ', ' danke ', ' bitte ']
        
        if any(trigger in f" {reply.lower()} " for trigger in foreign_triggers):
            print("⚠️ IRON DOME: Foreign language detected. Fallback triggered.")
            text_lower = text.lower()
            if any(w in text_lower for w in ['hospital', 'doctor', 'ilaaz', 'bimar', 'medical', 'aarogyasri']):
                parsed['reply'] = "Namaste. Medical help ke liye 108 call karein. Aarogyasri: https://aarogyasri.telangana.gov.in/"
            elif any(w in text_lower for w in ['pension', 'ration', 'scheme', 'yojana']):
                parsed['reply'] = "Namaste. Scheme ke liye Meeseva: https://ts.meeseva.telangana.gov.in/"
            else:
                parsed['reply'] = "Namaste. Kripya apni samasya detail mein batayein. Hum madad karenge."
        
        parsed['detected_language'] = parsed.get('detected_language', detected_lang)
        return parsed
        
    except Exception as e:
        print(f"❌ OSD Brain Error: {e}")
        return {
            "intent": "CHAT",
            "detected_language": detected_lang,
            "reply": "Namaste. Main aapki seva mein hoon. Kaise madad kar sakta hoon?",
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
    
    CTO CODE RED FIX: Use proper image_url format for OpenAI Vision API.
    """
    try:
        media_base64 = base64.b64encode(media_data).decode('utf-8')
        
        # Determine correct MIME type for the Vision API
        if 'pdf' in media_type.lower():
            # PDFs need special handling - convert first page to image
            print("📄 PDF detected - using PDF extraction mode")
            content_type = "application/pdf"
        elif 'png' in media_type.lower():
            content_type = "image/png"
        elif 'gif' in media_type.lower():
            content_type = "image/gif"
        elif 'webp' in media_type.lower():
            content_type = "image/webp"
        else:
            content_type = "image/jpeg"
        
        print(f"📎 Processing media: type={content_type}, size={len(media_data)} bytes")
        
        # For images, use direct OpenAI Vision API format which is more reliable
        if content_type.startswith('image/'):
            from openai import AsyncOpenAI
            
            client = AsyncOpenAI(
                api_key=EMERGENT_LLM_KEY,
                base_url="https://emergent-z1k3lu-v2.openai.azure.com/"
            )
            
            response = await client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert OCR system for government grievance documents in India.
Your task is DEEP OCR with ENGLISH NORMALIZATION.

CRITICAL INSTRUCTIONS:
1. The document may contain MIXED LANGUAGES (Hindi, Telugu, Tamil, English mixed together)
2. You MUST identify and extract ALL entities regardless of script
3. ALL OUTPUT FIELDS MUST BE IN ENGLISH - transliterate/translate everything

ENTITY EXTRACTION RULES:
- NAME: Look for "Name", "Applicant", "नाम", "పేరు", "பெயர்" etc. TRANSLITERATE to English (e.g., "राम कुमार" → "Ram Kumar")
- AREA: Look for "Mandal", "Village", "Ward", "मंडल", "गांव", "మండలం", "గ్రామం". TRANSLITERATE accurately (e.g., "अल्वाल" → "Alwal")
- CONTACT: Extract any 10-digit phone numbers
- CATEGORY: Map to official English categories only
- DESCRIPTION: Read entire content in any language, summarize in CLEAR ENGLISH

OFFICIAL CATEGORIES (pick one):
Water & Irrigation, Agriculture, Health & Sanitation, Education, Infrastructure & Roads, 
Law & Order, Welfare Schemes, Electricity, Forests & Environment, Finance & Taxation, 
Urban & Rural Development, Miscellaneous"""
                    },
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Perform DEEP OCR on this document/image.

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
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{content_type};base64,{media_base64}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=1000,
                temperature=0.2
            )
            
            result = response.choices[0].message.content
        else:
            # For PDFs, use the LlmChat wrapper
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"deep-ocr-{uuid.uuid4()}",
                system_message="""You are an expert OCR system. Extract text and summarize in English."""
            ).with_model("openai", "gpt-4o")
            
            msg = UserMessage(
                text="Extract all text from this PDF and provide a summary.",
                file_contents=[FileContent(content_type=content_type, file_content_base64=media_base64)]
            )
            result = await chat.send_message(msg)
        
        clean_result = result.replace('```json', '').replace('```', '').strip()
        extracted = json.loads(clean_result)
        
        # Ensure category is from official list
        if extracted.get('category') not in OFFICIAL_CATEGORIES:
            extracted['category'] = map_to_official_category(extracted.get('category', ''))
        
        print(f"✅ OCR extraction successful: {extracted.get('description', '')[:100]}...")
        return extracted
        
    except Exception as e:
        print(f"❌ Deep OCR extraction error: {e}")
        import traceback
        traceback.print_exc()
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
                print("⚠️ FFmpeg conversion timed out")
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


@router.post("/analyze_image")
async def analyze_image_endpoint(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Dedicated Image Analysis Endpoint using Vision Model.
    Extracts grievance information from images (JPG, PNG, etc.)
    with enhanced OCR and context understanding.
    """
    try:
        content = await file.read()
        media_type = file.content_type or "image/jpeg"
        
        if not media_type.startswith('image/'):
            raise HTTPException(status_code=400, detail="Only image files are supported by this endpoint")
        
        # Use the enhanced vision processing
        extracted = await process_image_with_vision(content, media_type)
        
        if extracted:
            return {"success": True, "data": extracted}
        else:
            return {"success": False, "error": "Could not extract information from image"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


async def process_image_with_vision(image_data: bytes, content_type: str) -> Dict[str, Any]:
    """
    Process image using GPT-4o Vision model for enhanced extraction.
    This function is specifically optimized for grievance-related images.
    """
    try:
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"vision-analysis-{uuid.uuid4()}",
            system_message="""You are an expert document analyzer for Indian government grievance systems.
Your task is to extract grievance information from images with HIGH PRECISION.

EXTRACTION RULES:
1. **Name**: Look for applicant name, petitioner name, or any name field. Transliterate to English if in other scripts.
2. **Contact**: Extract 10-digit Indian phone numbers (starting with 6,7,8,9)
3. **Area**: Look for Mandal, Village, Town, Ward, District names. Transliterate accurately.
4. **Category**: Map the issue to one of these EXACT categories:
   - Water & Irrigation, Agriculture, Forests & Environment
   - Health & Sanitation, Education, Infrastructure & Roads
   - Law & Order, Welfare Schemes, Finance & Taxation
   - Urban & Rural Development, Electricity, Miscellaneous
5. **Description**: Summarize the grievance/issue in clear English (max 200 words)
6. **Urgency**: Detect if it's an emergency (CRITICAL) or routine matter

VISUAL ANALYSIS:
- If image shows damaged infrastructure (road, bridge, building) → Infrastructure & Roads
- If image shows water logging, dry taps, dirty water → Water & Irrigation
- If image shows garbage, open drains, health hazard → Health & Sanitation
- If image shows broken power lines, transformer → Electricity
- If image shows documents/forms → Extract text content

OUTPUT FORMAT (JSON only, no markdown):
{
    "name": "English transliterated name or null",
    "contact": "10-digit phone or null",
    "area": "Location/Village/Mandal name or null",
    "category": "One of the 12 official categories",
    "description": "Clear English description of the issue",
    "urgency": "CRITICAL/HIGH/MEDIUM/LOW",
    "language": "Original language code (en/te/hi/ta/kn/ml/bn)"
}"""
        ).with_model("openai", "gpt-4o")
        
        msg = UserMessage(
            text="Analyze this image and extract grievance information. If it's a document, perform OCR. If it's a photo of an issue (road damage, water problem, etc.), describe the problem.",
            file_contents=[FileContent(content_type=content_type, file_content_base64=image_base64)]
        )
        
        result = await chat.send_message(msg)
        clean_result = result.replace('```json', '').replace('```', '').strip()
        extracted = json.loads(clean_result)
        
        # Ensure category is from official list
        if extracted.get('category') not in OFFICIAL_CATEGORIES:
            extracted['category'] = map_to_official_category(extracted.get('category', ''))
        
        return extracted
        
    except Exception as e:
        print(f"❌ Vision analysis error: {e}")
        return None


@router.post("/transcribe")
async def transcribe_endpoint(
    file: UploadFile = File(None),
    audio: UploadFile = File(None),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Transcribe audio file (supports WebM from web frontend and OGG from WhatsApp).
    Accepts both 'file' and 'audio' form field names for flexibility.
    Returns original text, detected language, and English translation if needed.
    """
    # Accept either 'file' or 'audio' field name
    upload_file = file or audio
    if not upload_file:
        raise HTTPException(status_code=400, detail="No audio file provided. Use 'file' or 'audio' field.")
    
    try:
        content = await upload_file.read()
        content_type = upload_file.content_type or "audio/webm"
        
        print(f"🎤 Transcribe request: {len(content)} bytes, type: {content_type}")
        
        transcript = await transcribe_audio(content, content_type)
        
        if transcript:
            detected_lang = detect_language(transcript)
            lang_name = {
                'te': 'Telugu', 'hi': 'Hindi', 'ta': 'Tamil',
                'kn': 'Kannada', 'ml': 'Malayalam', 'bn': 'Bengali',
                'en': 'English'
            }.get(detected_lang, 'Unknown')
            
            # Translate to English if not already English
            english_translation = transcript
            if detected_lang != 'en':
                try:
                    english_translation = await translate_text(transcript, 'en')
                except Exception:
                    english_translation = transcript
            
            return {
                "success": True, 
                "text": transcript,
                "original": transcript,
                "language": detected_lang,
                "language_detected": lang_name,
                "english_translation": english_translation
            }
        
        raise HTTPException(status_code=500, detail="Transcription failed - no text returned")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Transcription endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/transcribe-audio")
async def transcribe_audio_web_endpoint(
    audio: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """
    CTO MANDATE: Endpoint for Web Frontend Voice Recorder.
    Receives an audio blob (.webm), transcribes with Whisper.
    This is the endpoint the VoiceRecorder.jsx calls.
    """
    try:
        content = await audio.read()
        content_type = audio.content_type or "audio/webm"
        
        print(f"🎤 Web audio received: {len(content)} bytes, type: {content_type}")
        
        transcript = await transcribe_audio(content, content_type)
        
        if transcript:
            detected_lang = detect_language(transcript)
            lang_name = {
                'te': 'Telugu', 'hi': 'Hindi', 'ta': 'Tamil',
                'kn': 'Kannada', 'ml': 'Malayalam', 'bn': 'Bengali',
                'en': 'English'
            }.get(detected_lang, 'Unknown')
            
            return {
                "success": True,
                "text": transcript,
                "language_detected": lang_name
            }
        
        raise HTTPException(status_code=500, detail="Could not transcribe audio")
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Web transcription error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
