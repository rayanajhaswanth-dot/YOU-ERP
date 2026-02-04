"""
YOU - Governance ERP AI Routes
Updated with Emergent Integrations for Whisper transcription
"""
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user, TokenData
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
from emergentintegrations.llm.openai import OpenAISpeechToText
from datetime import datetime, timedelta, timezone
import os
import asyncio
import tempfile
import subprocess
import uuid
import json

router = APIRouter()

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

# ==============================================================================
# KNOWLEDGE BASE
# ==============================================================================

SYSTEM_PROMPT = """
You are the AI Assistant for an MLA (Member of Legislative Assembly) in India.
JURISDICTION: Civic Issues, Welfare Schemes, Government Policies.
You help constituents with queries and grievance registration.

For QUERIES: Provide helpful, accurate information about schemes and policies.
For GRIEVANCES: Classify and prioritize them appropriately.

OUTPUT FORMAT: JSON { "type": "GRIEVANCE"|"QUERY", "category": "...", "priority": "...", "response_text": "..." }
"""

SCHEME_DATA = {
    "rajiv yuva kiranam": "Rajiv Yuva Kiranam is a Youth Skill Development scheme for ages 18-35 in Telangana. It provides free training in various skills along with a stipend.",
    "rythu bandhu": "Rythu Bandhu is a farmer investment support scheme providing Rs. 10,000 per acre per year to land-owning farmers in Telangana.",
    "asara pension": "Asara Pension scheme provides monthly pension of Rs. 2,016 to eligible beneficiaries including elderly, widows, disabled persons, and weavers.",
    "kalyana lakshmi": "Kalyana Lakshmi provides Rs. 1,00,116 for marriage of girls from economically weaker sections.",
    "aarogyasri": "Aarogyasri Health Insurance provides free treatment up to Rs. 5 lakhs per family per year for BPL families.",
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


def analyze_interaction(text: str, sender_phone: str) -> dict:
    """
    Analyze text to determine if it's a QUERY or GRIEVANCE
    Uses keyword matching for schemes (RAG-Lite approach)
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


def categorize_text(text: str) -> tuple:
    """
    Categorize text using 11-Sector Framework
    Returns: (category, priority_level, deadline_hours)
    """
    text_lower = text.lower()
    
    # Emergency keywords - CRITICAL priority
    critical_keywords = ["fire", "accident", "current", "open wire", "shock", "danger", "emergency", "death", "collapse", "అత్యవసరం", "ప్రమాదం", "आग", "दुर्घटना"]
    if any(k in text_lower for k in critical_keywords):
        return ("Emergency", "CRITICAL", 4)
    
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
    if detected_category in ["Health & Sanitation", "Law & Order", "Electricity", "Emergency"]:
        return (detected_category, "CRITICAL", 4)
    elif detected_category in ["Water & Irrigation", "Infrastructure & Roads", "Agriculture"]:
        return (detected_category, "HIGH", 24)
    elif detected_category in ["Welfare Schemes", "Education"]:
        return (detected_category, "MEDIUM", 72)
    else:
        return (detected_category, "LOW", 336)


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


@router.post("/analyze_priority")
def analyze_priority_endpoint(request: GrievanceAnalysis):
    """
    11-Sector Governance Framework Priority Analysis
    """
    res = analyze_interaction(request.text, "0000000000")
    category, priority, deadline = categorize_text(request.text)
    
    return {
        "priority_level": priority,
        "category": category,
        "deadline_hours": deadline,
        "reason": f"Classified under {category}"
    }


@router.post("/transcribe")
async def transcribe_audio_endpoint(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Transcribe audio file using Emergent Whisper
    """
    try:
        content = await file.read()
        content_type = file.content_type or "audio/ogg"
        
        transcript = await transcribe_audio(content, content_type)
        
        if transcript:
            return {"success": True, "text": transcript}
        else:
            raise HTTPException(status_code=500, detail="Transcription failed - empty result")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze-grievance")
async def analyze_grievance(
    data: AIAnalysisRequest,
    current_user: TokenData = Depends(get_current_user)
):
    """
    AI-powered grievance analysis using Gemini
    """
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"grievance-{current_user.user_id}",
            system_message="You are an AI assistant helping analyze constituent grievances for Indian legislators. Provide priority scores (1-10) and actionable resolution steps."
        ).with_model("gemini", "gemini-2.0-flash")
        
        analysis_prompt = f"""Analyze this constituent grievance and provide:
1. Priority score (1-10, where 10 is most urgent)
2. Issue category (Infrastructure, Healthcare, Education, Employment, Social Welfare, Other)
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
    """
    Generate AI response for drafting communications
    """
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"response-{current_user.user_id}",
            system_message="You are an AI assistant helping Indian legislators draft professional responses. Be formal, empathetic, and solution-oriented. Consider local context and government protocols."
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
    """
    Generate AI draft for social media broadcast
    """
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"broadcast-{current_user.user_id}",
            system_message="You are a social media content creator for an Indian politician. Create engaging, professional posts that connect with constituents while maintaining dignity of the office."
        ).with_model("gemini", "gemini-2.0-flash")
        
        platform_context = data.context if data.context else "general social media"
        
        broadcast_prompt = f"""Create a social media post for {platform_context}:

Topic: {data.prompt}

Requirements:
- Engaging and accessible language
- Professional tone suitable for a public representative
- Include relevant hashtags
- Keep within typical platform character limits

Provide the post text and 2-3 hashtag suggestions."""
        
        user_message = UserMessage(text=broadcast_prompt)
        response = await chat.send_message(user_message)
        
        return {"draft": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
