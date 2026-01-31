from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user, TokenData
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
from datetime import datetime, timedelta, timezone
import os
import asyncio
import tempfile
import uuid
import json

router = APIRouter()

class AIAnalysisRequest(BaseModel):
    text: str
    analysis_type: str

class AIGenerateRequest(BaseModel):
    prompt: str
    context: Optional[str] = None

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

@router.post("/analyze-grievance")
async def analyze_grievance(
    data: AIAnalysisRequest,
    current_user: TokenData = Depends(get_current_user)
):
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"grievance-{current_user.user_id}",
            system_message="You are an AI assistant helping analyze constituent grievances for Indian legislators. Provide priority scores (1-10) and actionable resolution steps."
        ).with_model("gemini", "gemini-3-flash-preview")
        
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
        raise HTTPException(status_code=500, detail=f"AI analysis failed: {str(e)}")

@router.post("/generate-constituency-summary")
async def generate_constituency_summary(
    current_user: TokenData = Depends(get_current_user)
):
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"summary-{current_user.politician_id}",
            system_message="You are an AI assistant providing executive summaries for Indian legislators about their constituency."
        ).with_model("gemini", "gemini-3-pro-preview")
        
        summary_prompt = """Generate a brief 'State of the Union' summary for a constituency with these characteristics:
- Urban/Rural mix
- Key issues: Infrastructure development, Employment generation
- Recent progress: Road construction projects, skill development programs

Provide a 3-4 sentence executive summary highlighting current status and immediate priorities."""
        
        user_message = UserMessage(text=summary_prompt)
        response = await chat.send_message(user_message)
        
        return {"summary": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Summary generation failed: {str(e)}")

@router.post("/generate-campaign-suggestions")
async def generate_campaign_suggestions(
    data: AIGenerateRequest,
    current_user: TokenData = Depends(get_current_user)
):
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"campaign-{current_user.politician_id}",
            system_message="You are an AI assistant suggesting grassroots campaign actions for Indian legislators based on constituent feedback."
        ).with_model("gemini", "gemini-3-flash-preview")
        
        campaign_prompt = f"""Based on recurring constituent issues, suggest 3 specific grassroots campaign actions:

Context: {data.context or 'General constituency engagement'}
Recent trends: {data.prompt}

Provide actionable suggestions with expected impact."""
        
        user_message = UserMessage(text=campaign_prompt)
        response = await chat.send_message(user_message)
        
        return {"suggestions": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Campaign suggestion failed: {str(e)}")

@router.post("/polish-post")
async def polish_social_post(
    data: AIGenerateRequest,
    current_user: TokenData = Depends(get_current_user)
):
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"post-{current_user.user_id}",
            system_message="You are a social media expert helping Indian legislators craft engaging posts. Keep posts authentic, culturally appropriate, and platform-optimized."
        ).with_model("gemini", "gemini-3-flash-preview")
        
        polish_prompt = f"""Improve this social media post for an Indian legislator:

Original: {data.prompt}

Provide 3 versions:
1. For WhatsApp/Facebook (conversational, warm)
2. For Twitter/X (concise, impactful, max 280 chars)
3. For Instagram (engaging, visual-focused)"""
        
        user_message = UserMessage(text=polish_prompt)
        response = await chat.send_message(user_message)
        
        return {"polished_versions": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Post polishing failed: {str(e)}")

@router.post("/analyze-sentiment")
async def analyze_sentiment(
    data: AIAnalysisRequest,
    current_user: TokenData = Depends(get_current_user)
):
    try:
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id=f"sentiment-{current_user.user_id}",
            system_message="You are a sentiment analysis expert analyzing social media comments and public feedback for Indian legislators."
        ).with_model("gemini", "gemini-3-flash-preview")
        
        sentiment_prompt = f"""Analyze the sentiment of this social media comment:

Comment: {data.text}

Provide:
1. Sentiment score (-1 to 1, where -1 is very negative, 0 is neutral, 1 is very positive)
2. Key emotion (Positive, Negative, Neutral, Mixed)
3. Main topic/issue mentioned

Respond in JSON format with keys: score, emotion, topic"""
        
        user_message = UserMessage(text=sentiment_prompt)
        response = await chat.send_message(user_message)
        
        return {"sentiment": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Sentiment analysis failed: {str(e)}")


@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    current_user: TokenData = Depends(get_current_user)
):
    """
    Transcribe audio file using Gemini 2.0 Flash.
    Supports voice notes in local Indian languages and provides translation.
    Returns: { original: str, english_translation: str, language_detected: str }
    """
    try:
        # Validate file type
        allowed_types = ['audio/webm', 'audio/wav', 'audio/mp3', 'audio/mpeg', 'audio/ogg', 'audio/m4a', 'audio/x-m4a']
        content_type = audio.content_type or 'audio/webm'
        
        # Create a temporary file to store the audio
        temp_dir = tempfile.gettempdir()
        file_extension = '.webm' if 'webm' in content_type else '.wav'
        temp_filename = f"{uuid.uuid4()}{file_extension}"
        temp_path = os.path.join(temp_dir, temp_filename)
        
        # Save the uploaded file
        content = await audio.read()
        with open(temp_path, 'wb') as f:
            f.write(content)
        
        try:
            # Use Gemini 2.0 Flash for audio transcription
            chat = LlmChat(
                api_key=EMERGENT_LLM_KEY,
                session_id=f"transcribe-{current_user.user_id}-{uuid.uuid4()}",
                system_message="You are an expert audio transcription assistant specializing in Indian languages. You can accurately transcribe audio in Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, and other Indian regional languages."
            ).with_model("gemini", "gemini-2.0-flash")
            
            # Create file content for the audio
            audio_file = FileContentWithMimeType(
                file_path=temp_path,
                mime_type=content_type if content_type in allowed_types else 'audio/webm'
            )
            
            transcription_prompt = """Listen to this audio recording carefully. Transcribe it exactly as spoken.

If the audio is in a local Indian language (Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi, or any other regional language):
1. Provide the original transcription in the native script or romanized form
2. Provide an accurate English translation

Respond ONLY with a valid JSON object in this exact format (no markdown, no code blocks):
{
    "original": "the exact transcription of what was spoken",
    "english_translation": "the English translation (same as original if already in English)",
    "language_detected": "the detected language (e.g., Hindi, Tamil, English, Telugu, etc.)"
}"""
            
            user_message = UserMessage(
                text=transcription_prompt,
                file_contents=[audio_file]
            )
            
            response = await chat.send_message(user_message)
            
            # Parse the JSON response
            try:
                # Clean up response - remove markdown code blocks if present
                clean_response = response.strip()
                if clean_response.startswith('```'):
                    clean_response = clean_response.split('\n', 1)[1]
                    if clean_response.endswith('```'):
                        clean_response = clean_response[:-3]
                    clean_response = clean_response.strip()
                
                result = json.loads(clean_response)
                return {
                    "original": result.get("original", ""),
                    "english_translation": result.get("english_translation", ""),
                    "language_detected": result.get("language_detected", "Unknown")
                }
            except json.JSONDecodeError:
                # If JSON parsing fails, return raw response as original
                return {
                    "original": response,
                    "english_translation": response,
                    "language_detected": "Unknown"
                }
                
        finally:
            # Clean up temp file
            if os.path.exists(temp_path):
                os.remove(temp_path)
                
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audio transcription failed: {str(e)}")


# --- MULTI-LINGUAL LEGISLATIVE AI (Chat Bot Response) ---

class ChatRequest(BaseModel):
    message: str
    sender_phone: Optional[str] = None

class GrievanceAnalysis(BaseModel):
    text: str
    category: Optional[str] = "Miscellaneous"

# CONSTITUTIONAL AMBIT (Legislative vs Executive)
OUT_OF_PURVIEW_KEYWORDS = [
    "personal loan", "money", "debt", "court case", "police bail", 
    "divorce", "private dispute", "transfer", "promotion", "job offer",
    "personal financial help", "loan waiver"
]

# 11 GOVERNANCE CATEGORIES (Keywords Mapping)
CATEGORY_KEYWORDS = {
    "Water & Irrigation": ["water", "irrigation", "canal", "borewell", "tank", "drinking", "pipeline"],
    "Agriculture": ["crop", "seed", "farmer", "fertilizer", "msp", "drought", "harvest", "grain"],
    "Forests & Environment": ["forest", "tree", "pollution", "waste", "dumping", "environment", "plastic"],
    "Health & Sanitation": ["hospital", "doctor", "medicine", "dengue", "garbage", "sanitation", "clean", "drain", "mosquito"],
    "Education": ["school", "college", "teacher", "student", "exam", "book", "scholarship", "midday meal"],
    "Infrastructure & Roads": ["road", "pothole", "bridge", "building", "street light", "construction", "cement"],
    "Law & Order": ["police", "theft", "crime", "safety", "fight", "harassment", "illegal"],
    "Welfare Schemes": ["pension", "ration", "housing", "scheme", "aadhaar", "beneficiary", "support"],
    "Finance & Taxation": ["tax", "funds", "budget", "finance", "gst"],
    "Urban & Rural Development": ["panchayat", "municipality", "park", "community hall", "development", "permit"],
    "Miscellaneous": []
}

OFFICIAL_INDIAN_LANGUAGES = {
    "hi": "Namaste",  # Hindi
    "te": "Namaskaram",  # Telugu
    "ta": "Vanakkam",  # Tamil
    "kn": "Namaskara",  # Kannada
    "ml": "Namaskaram",  # Malayalam
    "bn": "Nomoshkar",  # Bengali
    "mr": "Namaskar",  # Marathi
    "gu": "Namaste",  # Gujarati
    "pa": "Sat Sri Akal"  # Punjabi
}

def detect_language_script(text):
    """Simple script detection for major Indian languages"""
    if any('\u0900' <= c <= '\u097F' for c in text): return "hi"  # Devanagari
    if any('\u0C00' <= c <= '\u0C7F' for c in text): return "te"  # Telugu
    if any('\u0B80' <= c <= '\u0BFF' for c in text): return "ta"  # Tamil
    if any('\u0C80' <= c <= '\u0CFF' for c in text): return "kn"  # Kannada
    return "en"

@router.post("/chat_response")
def get_bot_response(request: ChatRequest):
    """
    Logic Flow 1-5: Strict Governance Conversationalist
    Multi-lingual support with Legislative vs Executive guardrails
    """
    msg = request.message.lower()
    lang_code = detect_language_script(request.message)
    
    # 1. Greeting (Multi-Lingual)
    if any(x in msg for x in ["hi", "hello", "namaste", "start", "vanakkam"]):
        response_map = {
            "te": "నమస్కారం! నేను మీ ఎమ్మెల్యే గారి ఆఫీస్ బాట్ ని. దయచేసి మీ సమస్యను (నీరు, రోడ్లు, పెన్షన్, మొదలైనవి) పంపండి.",
            "hi": "नमस्ते! मैं आपके विधायक का कार्यालय सहायक हूं। कृपया अपनी समस्या (पानी, सड़क, पेंशन, आदि) भेजें।",
            "ta": "வணக்கம்! நான் உங்கள் எம்.எல்.ஏ அலுவலக உதவியாளர். உங்கள் குறைகளை இங்கே பகிரவும்.",
            "en": "Greetings! I am the AI Assistant. Please share your grievance regarding categories like Water, Roads, Health, or Welfare."
        }
        return {"response": response_map.get(lang_code, response_map["en"])}

    # 2. Strict Purview Check (Legislative vs Private)
    if any(k in msg for k in OUT_OF_PURVIEW_KEYWORDS):
        return {
            "response": "I apologize, but personal financial or legal matters are outside the MLA/MP's purview. We handle Civic Issues, Infrastructure, and Welfare Schemes."
        }

    # 3. Informal vs Formal Query
    if "?" in msg or "how to" in msg:
        return {"response": "That sounds like a query regarding governance. Could you please specify the Scheme or Department? For grievances, please provide: Name, Area, and Issue Description."}

    # 4. Standard Acknowledgment for Grievance Input
    return {"response": "Received. I am categorizing your request under the relevant department (e.g., Health, Infrastructure) for immediate action."}

@router.post("/analyze_priority")
def analyze_priority(request: GrievanceAnalysis):
    """
    Logic Flow 6: 11-Sector Governance Framework
    Enhanced Categorization & Priority Matrix
    """
    text = request.text.lower()
    user_cat = request.category
    
    # Detect Category based on Keywords
    detected_category = "Miscellaneous"
    for cat, keywords in CATEGORY_KEYWORDS.items():
        if any(k in text for k in keywords):
            detected_category = cat
            break
            
    # If user manually selected a category, trust it, otherwise use detected
    final_category = user_cat if user_cat and user_cat != "Miscellaneous" else detected_category

    # Assign Priority based on Sector Criticality
    priority = "MEDIUM"
    deadline_hours = 168  # 7 Days

    if final_category in ["Health & Sanitation", "Law & Order"]:
        priority = "CRITICAL"
        deadline_hours = 4
    elif final_category in ["Water & Irrigation", "Infrastructure & Roads", "Agriculture"]:
        priority = "HIGH"
        deadline_hours = 24
    elif final_category in ["Welfare Schemes", "Education"]:
        priority = "MEDIUM"
        deadline_hours = 72
        
    # Contextual overrides (e.g., "Fire" is critical regardless of category)
    if "fire" in text or "accident" in text or "shock" in text:
        priority = "CRITICAL"
        deadline_hours = 2

    return {
        "priority_level": priority,
        "category": final_category,
        "deadline_hours": deadline_hours,
        "reason": f"Classified under {final_category}"
    }