# YOU - Governance ERP & Workflow Automation for Legislators

## Product Overview
A production-ready SaaS platform for Indian political leaders featuring AI-powered governance tools.

## Changelog

### 2026-02-04 (CRITICAL FIXES)
**Issue 1 FIXED - File Upload from Device:**
- Added `POST /api/grievances/{id}/upload-file` endpoint for direct file upload
- Frontend now has toggle between "From Device" and "From URL" upload methods
- Drag-and-drop photo upload with file validation (image only, max 10MB)

**Issue 2 FIXED - Voice Message Transcription:**
- **ROOT CAUSE 1**: Direct OpenAI client incompatible with Emergent API Key format (`sk-emergent-*`)
- **ROOT CAUSE 2**: WhatsApp sends voice messages in OGG/Opus format, but Whisper only supports: mp3, mp4, mpeg, mpga, m4a, wav, webm
- **FIX 1**: Using `emergentintegrations.llm.openai.OpenAISpeechToText` class instead of direct OpenAI client
- **FIX 2**: Installed FFmpeg and added OGG → MP3 conversion before transcription
- **Updated Files**: `whatsapp_routes.py` and `ai_routes.py` both now use Emergent wrapper with FFmpeg conversion

**Issue 3 FIXED - Category Mapping:**
- Enhanced CATEGORY_KEYWORDS with more Indian language terms
- Added "Electricity" as separate category
- Frontend normalizes "General" to "Miscellaneous" for display
- Improved category detection algorithm (counts keyword matches)

**Issue 4 FIXED - Mixed Language Responses:**
- AI intent detection now explicitly requires responses in detected language only
- Added `query_response` template for each language
- No English text mixed in Telugu/Hindi/Tamil conversations
- Added complete response templates for all message types in all languages

### 2026-01-31
- **CRITICAL FIX: `priority_level` Refactor Complete**: Fixed duplicate route definition in `ai_routes.py`
- **Backend API Verified**: `/api/ai/analyze_priority` returns `priority_level`, `category`, `deadline_hours`
- **Help People Console**: KPI cards, critical issues section, grievance registration form working

### 2025-01-29
- **Campaign Analytics Module Complete**: Added `/analytics` route
- **Sidebar Navigation Updated**: Added Analytics link
- **Meta Graph API Integration**: Fetches Instagram posts with metrics

## Tech Stack
- **Frontend**: React + TailwindCSS + Recharts + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **AI**: Gemini 2.0 Flash (intent detection), OpenAI Whisper (voice), GPT-4o (image OCR)
- **Messaging**: Twilio WhatsApp API

## Database Schema (User's Live DB)
### grievances table columns:
- id, politician_id, status, issue_type, village, description
- ai_priority, created_at, priority_level, deadline_timestamp
- assigned_official_phone, media_url, category
- citizen_name, citizen_phone
- resolution_image_url (for photo verification)
- feedback_rating (1-5 stars from citizen)
- language_preference (for multi-lingual responses)

## Core Modules
1. **Briefing Room** - Executive dashboard with KPIs and real-time feeds
2. **Help People** - WhatsApp grievance bot with 10-step workflow
3. **Send News** - AI-powered broadcast drafting
4. **Analytics** - Campaign performance metrics

## WhatsApp Bot Logic Flow
1. **Greeting Detection**: Detects greetings in any Indian language, responds in same language
2. **Query Handling**: Answers questions about schemes/policies conversationally
3. **Out of Purview Check**: Politely declines personal matters (loans, court cases)
4. **Grievance Registration**: Only actual problems get registered with ticket
5. **Resolution Notification**: Citizen gets WhatsApp message when resolved
6. **Feedback Collection**: Citizen rates service 1-5 stars

## API Endpoints

### WhatsApp
- `POST /api/whatsapp/webhook` - Twilio webhook for incoming messages
- `GET /api/whatsapp/status` - Bot status and features
- `POST /api/whatsapp/send` - Send outbound message
- `POST /api/whatsapp/send-resolution` - Send resolution notification

### Grievances
- `GET /api/grievances/` - List all grievances
- `POST /api/grievances/` - Create new grievance
- `GET /api/grievances/{id}` - Get single grievance
- `GET /api/grievances/metrics` - Comprehensive metrics
- `PUT /api/grievances/{id}/start-work` - Start work (10-step)
- `PUT /api/grievances/{id}/upload-resolution-photo` - Upload photo (10-step)
- `PUT /api/grievances/{id}/resolve` - Mark resolved (10-step)
- `PUT /api/grievances/{id}/feedback` - Record rating (10-step)
- `PUT /api/grievances/{id}/assign` - Assign to official

### AI
- `POST /api/ai/analyze_priority` - 11-sector categorization
- `POST /api/ai/transcribe` - Voice transcription

## Test Credentials
- Email: `ramkumar@example.com`
- Password: `test123`

## Test Results (2026-02-04)
- Backend: 100% (16/16 tests passed)
- Frontend: 100% (all workflow features tested)
- WhatsApp bot multi-lingual: ✅ Working
- AI priority analysis: ✅ Returns priority_level
- 10-step workflow: ✅ Complete with photo verification

## Pending Tasks
- [ ] Test WhatsApp voice transcription live (Telugu, >30 seconds)
- [ ] Refine Broadcast Center (view past broadcast history)
- [ ] Expand Multi-Role Access Control
- [ ] Real-time WebSocket ticker
- [ ] Remove obsolete files (tickets_routes.py, HappinessReport.jsx)
