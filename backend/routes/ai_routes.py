from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from pydantic import BaseModel
from typing import Optional
from auth import get_current_user, TokenData
from emergentintegrations.llm.chat import LlmChat, UserMessage, FileContentWithMimeType
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