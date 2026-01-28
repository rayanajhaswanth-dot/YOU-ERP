import random
from textblob import TextBlob
from datetime import datetime, date
from database import supabase

# Mock Comments to simulate "Listening" to the public
# In Production, this would be replaced by requests.get(FACEBOOK_GRAPH_API)
MOCK_COMMENTS = [
    "The new road in Ward 5 is amazing! Great work.",
    "Why is the water supply still cut off? It's been 2 days!",
    "Thank you for the quick response on the street light issue.",
    "Corruption is high, nothing gets done without bribes.",
    "Love the new park renovation. Ideally need more benches.",
    "Traffic at the main junction is a nightmare.",
    "Proud of our MLA for visiting the flood victims.",
    "Garbage collection has stopped in our area. Please help.",
    "Street dogs are becoming a menace in the colony.",
    "Excellent initiative on the health camp!"
]

async def fetch_and_analyze_social_feed():
    """
    Cron Job Function: 
    1. Simulates fetching new comments from Social Media.
    2. Analyzes sentiment locally using TextBlob (No API Cost).
    3. Saves result to Supabase 'sentiment_analytics' table.
    """
    print("🔄 [Social Listener] Tuning into public sentiment...")
    
    # 1. Simulate fetching 3 random comments
    new_comments = random.sample(MOCK_COMMENTS, 3)
    
    # Count sentiments
    positive_count = 0
    negative_count = 0
    neutral_count = 0
    total_score = 0.0
    
    for comment in new_comments:
        # 2. Analyze (Local Python TextBlob)
        blob = TextBlob(comment)
        score = blob.sentiment.polarity  # Returns float: -1.0 (Bad) to 1.0 (Good)
        total_score += score
        
        # Categorize sentiment
        if score > 0.1:
            positive_count += 1
        elif score < -0.1:
            negative_count += 1
        else:
            neutral_count += 1
    
    # Determine Platform (Random for simulation)
    platform = random.choice(["facebook", "twitter", "whatsapp"])
    avg_score = total_score / len(new_comments) if new_comments else 0
    
    # Build data - use only basic columns that should exist
    # Note: Full functionality requires DB migration to be applied
    data = {
        "platform": platform
    }
    
    # 3. Store in DB
    try:
        response = supabase.table("sentiment_analytics").insert(data).execute()
        print(f"✅ [Social Listener] Processed {len(new_comments)} comments. Avg Sentiment: {avg_score:.2f} (👍{positive_count} 👎{negative_count} 😐{neutral_count})")
        print("⚠️  Note: Full data storage requires DB schema migration. Only platform stored.")
    except Exception as e:
        print(f"❌ [Social Listener] DB Error: {e}")
        print("💡 Hint: Run the schema migration SQL in Supabase SQL Editor to enable full functionality.")
