# YOU - Governance ERP & Workflow Automation for Legislators

## Product Overview
A production-ready SaaS platform for Indian political leaders featuring AI-powered governance tools.

## Changelog

### 2025-01-29
- **Campaign Analytics Module Complete**: Added `/analytics` route to App.js
- **Analytics Page UI**: KPI cards (Total Reach, Total Engagement, Posts Tracked) + Recent Broadcasts list with detailed metrics (Reach, Likes, Comments)
- **Sidebar Navigation Updated**: Added Analytics link with TrendingUp icon to Layout.jsx
- **Meta Graph API Integration**: Fetches Instagram posts with likes, comments, reach metrics in parallel

### 2025-01-28
- **Dashboard MVP Complete**: Implemented "The Briefing Room" with Executive Feed layout
- **KPIGrid Component**: 4 KPI cards (Approval Rating, Political Momentum, Active Criticals, Daily Engagement)
- **BroadcastWidget**: Collapsible AI-powered multi-platform content drafting
- **SentimentDashboard**: Executive Briefing with Digital Perception & Ground Stability metrics
- **GrievanceFeed**: Critical Alerts with WhatsApp deep-link assignment feature
- **Social Listener Service**: Background service for sentiment analysis simulation

### 2025-01-27
- **AI Reality Matrix Implemented**: `analyze_grievance()` function for keyword-based priority classification
- **Deep Link Feature Added**: `generate_assignment_link()` for official task assignment
- **Grievance Data Enhanced**: New fields `priority_level`, `deadline_timestamp`, `media_url`
- **Sentiment Engine**: TextBlob-based local sentiment analysis (no API cost)

## Tech Stack
- **Frontend**: React + TailwindCSS + Recharts
- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **AI**: OpenAI Whisper (voice), GPT-4o (images), Gemini (text), TextBlob (sentiment)
- **Messaging**: Twilio WhatsApp API

## Core Modules
1. **Briefing Room** - Executive dashboard with KPIs and real-time feeds
2. **Help People** - WhatsApp grievance bot with voice/image processing
3. **Send News** - AI-powered broadcast drafting
4. **Happiness Report** - Sentiment analytics dashboard

## API Endpoints
- `POST /api/dashboard/draft` - AI content drafting
- `GET /api/dashboard/grievances` - Critical issues feed
- `GET /api/dashboard/stats` - Dashboard statistics
- `POST /api/social/analyze` - Sentiment analysis
- `GET /api/social/dashboard` - Sentiment data for charts
- `POST /api/whatsapp/webhook` - WhatsApp message processing
- `POST /api/posts/publish` - Publish to Facebook/Instagram
- `GET /api/analytics/campaigns` - Campaign performance metrics (FB & IG)

## Database Schema Updates Required
```sql
ALTER TABLE grievances ADD COLUMN IF NOT EXISTS priority_level TEXT DEFAULT 'LOW';
ALTER TABLE grievances ADD COLUMN IF NOT EXISTS deadline_timestamp TIMESTAMPTZ;
ALTER TABLE grievances ADD COLUMN IF NOT EXISTS issue_type TEXT DEFAULT 'Other';
ALTER TABLE grievances ADD COLUMN IF NOT EXISTS media_url TEXT;
ALTER TABLE sentiment_analytics ADD COLUMN IF NOT EXISTS report_date DATE DEFAULT CURRENT_DATE;
ALTER TABLE sentiment_analytics ADD COLUMN IF NOT EXISTS positive_count INTEGER DEFAULT 0;
ALTER TABLE sentiment_analytics ADD COLUMN IF NOT EXISTS negative_count INTEGER DEFAULT 0;
ALTER TABLE sentiment_analytics ADD COLUMN IF NOT EXISTS neutral_count INTEGER DEFAULT 0;
```

## Pending Tasks
- [ ] Test WhatsApp voice transcription (Telugu, >30 seconds)
- [ ] Run Supabase schema migrations
- [ ] Connect real social media APIs
- [ ] Multi-role access control
- [ ] Real-time ticker with Socket.io
