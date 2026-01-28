import random
from textblob import TextBlob
from datetime import datetime
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
    # We randomize to simulate dynamic feed updates
    new_comments = random.sample(MOCK_COMMENTS, 3)
    
    results = []
    
    for comment in new_comments:
        # 2. Analyze (Local Python TextBlob)
        blob = TextBlob(comment)
        score = blob.sentiment.polarity # Returns float: -1.0 (Bad) to 1.0 (Good)
        
        # Determine Platform (Random for simulation)
        platform = random.choice(["facebook", "twitter", "whatsapp"])
        
        data = {
            "platform": platform,
            "sentiment_score": score,
            "mention_count": 1,
            "recorded_at": datetime.now().isoformat()
        }
        
        # 3. Store in DB
        try:
            # Insert into the 'sentiment_analytics' table created in schema
            response = supabase.table("sentiment_analytics").insert(data).execute()
            results.append(data)
        except Exception as e:
            print(f"❌ [Social Listener] DB Error: {e}")

    # Log summary for server console
    if results:
        avg_score = sum(r['sentiment_score'] for r in results) / len(results)
        print(f"✅ [Social Listener] Processed {len(results)} comments. Avg Sentiment: {avg_score:.2f}")
    else:
        print("⚠️ [Social Listener] No data processed.")
