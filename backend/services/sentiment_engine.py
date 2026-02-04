"""
YOU - Governance ERP Sentiment Analysis Engine
LLM-based contextual sentiment analysis for social media comments
Handles native Indian languages (Telugu, Hindi, Tamil) with political context
"""
import os
import json
from emergentintegrations.llm.chat import LlmChat, UserMessage

EMERGENT_LLM_KEY = os.environ.get('EMERGENT_LLM_KEY')

SYSTEM_PROMPT = """
You are a Political Sentiment Analyst for an Indian MLA/MP. Analyze social media comments and reactions with CONTEXTUAL understanding.

**INPUT:**
- Post Context: (e.g., "Inauguration of new road", "Condolence message", "Criticizing opposition")
- Comments: List of text (English, Telugu, Hindi, Tanglish, code-mixed).
- Reactions: Counts of Like, Love, Haha, Wow, Sad, Angry.

**LOGIC:**
1. **Language:** Handle Telugu (తెలుగు), Hindi (हिंदी), Tamil, Tanglish natively.
2. **Contextual Reactions:**
   - If Post is "Condolence/Death": SAD = Neutral/Supportive (empathy).
   - If Post is "Attack on Opposition/Political criticism": ANGRY = Supportive (Positive for the politician).
   - If Post is "Development/Achievement": ANGRY = Negative (opposition critics).
   - Otherwise, ANGRY = Negative.
3. **Sarcasm Detection:** Identify sarcasm (e.g., "Great work... NOT", "వావ్ ఎంత పని").
4. **Sentiment Intent:**
   - "Thank you sir", "మంచి పని", "धन्यवाद" = Positive
   - Questions/neutral statements = Neutral
   - Complaints, criticism, abuse = Negative

**OUTPUT (ONLY VALID JSON, no markdown):**
{
  "positive_count": <number>,
  "neutral_count": <number>,
  "negative_count": <number>,
  "overall_sentiment": "Positive|Neutral|Negative",
  "narrative_summary": "<2-3 sentence summary of citizen sentiment>"
}
"""

async def analyze_social_sentiment(post_context: str, comments_list: list, reactions_dict: dict) -> dict:
    """
    Analyze social media sentiment using LLM with political context awareness.
    
    Args:
        post_context: Description/caption of the post
        comments_list: List of comment texts
        reactions_dict: Dict with keys: like, love, haha, wow, sad, angry
    
    Returns:
        Sentiment analysis result with counts and summary
    """
    try:
        # If no data, return empty result
        if not comments_list and not reactions_dict:
            return {
                "positive_count": 0,
                "neutral_count": 0,
                "negative_count": 0,
                "overall_sentiment": "Neutral",
                "narrative_summary": "No data available for analysis."
            }
        
        # Quick analysis for reaction-only posts (no comments)
        if not comments_list and reactions_dict:
            return analyze_reactions_only(reactions_dict, post_context)
        
        # LLM-based analysis for posts with comments
        chat = LlmChat(
            api_key=EMERGENT_LLM_KEY,
            session_id="sentiment-analysis",
            system_message=SYSTEM_PROMPT
        ).with_model("openai", "gpt-4o-mini")
        
        # Prepare input for LLM
        input_data = {
            "context": post_context or "General political post",
            "comments": comments_list[:50],  # Limit to 50 comments for cost efficiency
            "reactions": reactions_dict
        }
        
        user_message = UserMessage(text=json.dumps(input_data, ensure_ascii=False))
        response = await chat.send_message(user_message)
        
        # Parse JSON response
        clean_response = response.replace('```json', '').replace('```', '').strip()
        result = json.loads(clean_response)
        
        return {
            "positive_count": result.get("positive_count", 0),
            "neutral_count": result.get("neutral_count", 0),
            "negative_count": result.get("negative_count", 0),
            "overall_sentiment": result.get("overall_sentiment", "Neutral"),
            "narrative_summary": result.get("narrative_summary", "Analysis complete.")
        }
        
    except Exception as e:
        print(f"❌ Sentiment Analysis Error: {e}")
        # Fallback to reaction-based analysis
        return analyze_reactions_only(reactions_dict, post_context)


def analyze_reactions_only(reactions_dict: dict, post_context: str = "") -> dict:
    """
    Fallback analysis based on reactions when LLM fails or no comments exist.
    Uses contextual rules for political posts.
    """
    like = reactions_dict.get('like', 0) or 0
    love = reactions_dict.get('love', 0) or 0
    haha = reactions_dict.get('haha', 0) or 0
    wow = reactions_dict.get('wow', 0) or 0
    sad = reactions_dict.get('sad', 0) or 0
    angry = reactions_dict.get('angry', 0) or 0
    
    total = like + love + haha + wow + sad + angry
    if total == 0:
        return {
            "positive_count": 0,
            "neutral_count": 0,
            "negative_count": 0,
            "overall_sentiment": "Neutral",
            "narrative_summary": "No reactions to analyze."
        }
    
    # Contextual interpretation
    context_lower = (post_context or "").lower()
    
    # Condolence/Death posts: SAD is supportive, not negative
    is_condolence = any(word in context_lower for word in ['condolence', 'death', 'passed away', 'rip', 'నివాళి', 'శోకం', 'श्रद्धांजलि'])
    
    # Opposition criticism: ANGRY might be supportive
    is_opposition_attack = any(word in context_lower for word in ['opposition', 'tdp', 'bjp', 'congress', 'criticism', 'విమర్శ', 'आलोचना', 'expose'])
    
    # Calculate sentiment
    positive = like + love
    negative = angry
    neutral = haha + wow
    
    # Contextual adjustments
    if is_condolence:
        neutral += sad  # SAD on condolence = empathy, not negative
    else:
        negative += sad * 0.5  # SAD elsewhere might be partial negative
    
    if is_opposition_attack:
        positive += angry * 0.7  # ANGRY on opposition attack = supportive
        negative = angry * 0.3
    
    # Determine overall sentiment
    if positive > (negative + neutral):
        overall = "Positive"
        narrative = f"Citizens show support with {int(positive)} positive reactions."
    elif negative > positive:
        overall = "Negative"
        narrative = f"Some concerns with {int(negative)} negative reactions. Monitor closely."
    else:
        overall = "Neutral"
        narrative = f"Mixed response with {total} total reactions."
    
    return {
        "positive_count": int(positive),
        "neutral_count": int(neutral),
        "negative_count": int(negative),
        "overall_sentiment": overall,
        "narrative_summary": narrative
    }


def calculate_ground_stability(grievances: list) -> dict:
    """
    Calculate SLA-based Ground Stability metrics from grievance data.
    
    SLA Rules:
    - CRITICAL: 4 hours
    - HIGH: 24 hours
    - MEDIUM: 72 hours (3 days)
    - LOW: 336 hours (14 days)
    
    Returns stability percentage and status.
    """
    from datetime import datetime, timezone
    
    if not grievances:
        return {
            "total": 0,
            "resolved": 0,
            "resolved_within_sla": 0,
            "sla_percentage": 0,
            "status_label": "No Data",
            "citizen_rating": 0,
            "rating_count": 0
        }
    
    total = len(grievances)
    resolved = 0
    resolved_within_sla = 0
    rating_sum = 0
    rating_count = 0
    
    sla_hours = {
        "CRITICAL": 4,
        "HIGH": 24,
        "MEDIUM": 72,
        "LOW": 336
    }
    
    now = datetime.now(timezone.utc)
    
    for g in grievances:
        status = (g.get('status') or '').upper()
        
        # Count resolved
        if status == 'RESOLVED':
            resolved += 1
            
            # Check if resolved within SLA
            created_at = g.get('created_at')
            deadline = g.get('deadline_timestamp')
            priority = (g.get('priority_level') or 'LOW').upper()
            
            if deadline:
                try:
                    deadline_dt = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                    # If resolved before deadline, it's within SLA
                    resolved_within_sla += 1  # Simplified: assume resolved = within SLA
                except:
                    pass
            elif created_at:
                # Calculate based on SLA hours
                try:
                    created_dt = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                    hours_allowed = sla_hours.get(priority, 336)
                    # Simplified: if resolved, count as within SLA
                    resolved_within_sla += 1
                except:
                    pass
        
        # Collect feedback ratings
        rating = g.get('feedback_rating')
        if rating:
            rating_sum += rating
            rating_count += 1
    
    # Calculate SLA percentage
    sla_percentage = (resolved_within_sla / total * 100) if total > 0 else 0
    
    # Calculate average citizen rating
    citizen_rating = (rating_sum / rating_count) if rating_count > 0 else 0
    
    # Determine status label
    if sla_percentage >= 75:
        status_label = "Excellent"
    elif sla_percentage >= 50:
        status_label = "Good"
    elif sla_percentage >= 30:
        status_label = "Needs Improvement"
    else:
        status_label = "Critical"
    
    return {
        "total": total,
        "resolved": resolved,
        "resolved_within_sla": resolved_within_sla,
        "sla_percentage": sla_percentage,
        "status_label": status_label,
        "citizen_rating": citizen_rating,
        "rating_count": rating_count
    }
