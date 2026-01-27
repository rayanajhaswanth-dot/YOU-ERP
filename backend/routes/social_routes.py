from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from textblob import TextBlob
from datetime import date
import os

from database import get_supabase

router = APIRouter()

class AnalysisRequest(BaseModel):
    text: str
    platform: str = "Generic"  # e.g., Twitter, WhatsApp, Facebook

@router.post("/analyze")
async def analyze_sentiment(request: AnalysisRequest):
    """
    Analyzes text sentiment and updates daily counters.
    Feature: Detects 'Negative Sentiment Spikes' as per PRD Section 3.
    """
    try:
        supabase = get_supabase()
        
        # 1. AI Analysis (Local TextBlob - No Paid API)
        blob = TextBlob(request.text)
        polarity = blob.sentiment.polarity  # Range: -1.0 (Bad) to 1.0 (Good)
        
        # 2. Categorize & Spike Detection
        sentiment_category = "neutral"
        spike_warning = False
        
        if polarity > 0.1:
            sentiment_category = "positive"
        elif polarity < -0.1:
            sentiment_category = "negative"
            # PRD Section 3: Metric for Negative Sentiment Spike
            # If sentiment is extremely negative, flag it for the 'Response Time' KPI
            if polarity < -0.6:
                spike_warning = True
        
        # 3. Database Aggregation (Read-Modify-Write)
        today_str = date.today().isoformat()
        politician_id = os.getenv("POLITICIAN_ID", "6e56793a-558b-4834-ab0d-36387159653a")
        
        # Check existing row for Today + Platform
        existing = supabase.table("sentiment_analytics").select("*")\
            .eq("report_date", today_str)\
            .eq("platform", request.platform)\
            .eq("politician_id", politician_id)\
            .execute()
        
        if existing.data:
            # Update existing row counters
            row_id = existing.data[0]['id']
            col_name = f"{sentiment_category}_count"
            current_val = existing.data[0].get(col_name, 0)
            
            supabase.table("sentiment_analytics").update({
                col_name: current_val + 1
            }).eq("id", row_id).execute()
        else:
            # Create new row for the day
            new_row = {
                "politician_id": politician_id,
                "platform": request.platform,
                "report_date": today_str,
                "positive_count": 1 if sentiment_category == "positive" else 0,
                "negative_count": 1 if sentiment_category == "negative" else 0,
                "neutral_count": 1 if sentiment_category == "neutral" else 0,
            }
            supabase.table("sentiment_analytics").insert(new_row).execute()
        
        return {
            "status": "success",
            "sentiment": sentiment_category,
            "score": polarity,
            "spike_detected": spike_warning  # Frontend can use this for visual alerts
        }
        
    except Exception as e:
        print(f"Sentiment Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/dashboard")
async def get_happiness_data():
    """
    Fetches aggregated data for the 'Happiness Report' Chart.
    Returns data sorted by date for the graph.
    """
    try:
        supabase = get_supabase()
        politician_id = os.getenv("POLITICIAN_ID", "6e56793a-558b-4834-ab0d-36387159653a")
        
        response = supabase.table("sentiment_analytics")\
            .select("*")\
            .eq("politician_id", politician_id)\
            .order("report_date", desc=True)\
            .limit(7)\
            .execute()
        
        return response.data
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
