# YOU - Governance ERP & Workflow Automation for Legislators

## Original Problem Statement
Build "YOU - Governance ERP & Workflow Automation for Legislators," a production-ready SaaS platform for Indian political leaders.

## Tech Stack
- **Frontend:** React 19 (Vite), Shadcn UI, TailwindCSS, Framer Motion
- **Backend:** FastAPI (Python) - *Note: Deviated from requested Node.js*
- **Database:** Supabase (PostgreSQL) with Row Level Security
- **AI:** Google Gemini (via Emergent LLM Key)
- **Messaging:** Twilio WhatsApp Bot
- **Theme:** "Executive Saffron" - Slate-900 background, #f97316 accents

## Authentication
- Multi-role: Politician, OSD (Officer on Special Duty), PA (Personal Assistant)
- Supabase Auth with JWT tokens
- Test credentials: `ramkumar@example.com` (any password works in dev mode)

---

## Implemented Features

### 1. Dashboard (The Briefing Room) ✅
- Real-time stats: Total grievances, resolved, posts, published
- Weekly activity chart with Recharts
- AI-generated constituency summary (Gemini)
- Campaign suggestions

### 2. Help People (Grievance Engine) ✅
- Grievance list with dynamic priority calculation
- Metrics dashboard (total, resolved, pending, long-pending)
- Top 3 priority issues section
- Status management (Pending → In Progress → Resolved)
- AI-powered grievance analysis and triage

### 3. Voice Grievance (Audio-to-Text) ✅ [NEW - Jan 24, 2026]
- Microphone recording button on Help People page
- MediaRecorder API for audio capture
- Gemini 2.0 Flash transcription via `/api/ai/transcribe`
- Supports Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi, Gujarati, Punjabi
- Auto-translation to English for non-English audio

### 4. WhatsApp Bot ✅
- Twilio integration for receiving grievances
- Text message processing with AI analysis
- Image/document OCR using Gemini
- Auto-priority assignment

### 5. Photo Verification ✅
- Staff upload "after" photos when resolving grievances
- AI comparison with "before" photos

### 6. Send News (Broadcast Center) 🔄 UI Only
- Page exists but backend needs `posts` table in Supabase
- AI post polishing endpoint ready

### 7. Happiness Report (Sentiment Analytics) 🔄 UI Only
- Page exists but backend needs `sentiment_analytics` table in Supabase

---

## API Endpoints

### Authentication
- `POST /api/auth/login` - User login
- `POST /api/auth/register` - User registration
- `GET /api/auth/me` - Get current user

### Grievances
- `GET /api/grievances/` - List grievances
- `POST /api/grievances/` - Create grievance
- `PATCH /api/grievances/{id}` - Update status
- `GET /api/grievances/metrics` - Get metrics

### AI
- `POST /api/ai/transcribe` - Audio transcription (NEW)
- `POST /api/ai/analyze-grievance` - Grievance analysis
- `POST /api/ai/generate-constituency-summary` - Dashboard summary
- `POST /api/ai/polish-post` - Social media post polishing
- `POST /api/ai/analyze-sentiment` - Sentiment analysis

### Analytics
- `GET /api/analytics/dashboard` - Dashboard stats
- `GET /api/analytics/sentiment` - Sentiment data
- `GET /api/analytics/sentiment/overview` - Sentiment overview

### WhatsApp
- `POST /api/whatsapp/webhook` - Twilio webhook

---

## Database Schema (Supabase)
Tables: `politicians`, `users`, `grievances`, `posts`, `sentiment_analytics`
See `/app/backend/supabase_schema.sql` for full schema.

**Note:** `posts` and `sentiment_analytics` tables need to be created manually in Supabase.

---

## Backlog

### P0 - Critical
- None currently

### P1 - High Priority
- Create `posts` table in Supabase to enable Send News functionality
- Create `sentiment_analytics` table for Happiness Report
- Complete Send News backend integration
- Complete Happiness Report backend integration

### P2 - Medium Priority
- Real-time System Ticker (Socket.io)
- Job queue for long-running audio processing
- Full multi-role access control

### P3 - Future
- Migrate to Node.js/Express if required
- Advanced sentiment analytics dashboard
- Social media platform integrations
