# YOU - Governance ERP & Workflow Automation for Legislators

## Product Overview
A production-ready SaaS platform for Indian political leaders featuring AI-powered governance tools.

## Changelog

### 2026-02-04 (MAJOR UPDATE)
- **COMPLETE WHATSAPP BOT REWRITE**: Fixed the bot to be conversationally intelligent:
  - **Multi-lingual Support**: Detects Indian language scripts (Telugu నమస్కారం, Hindi नमस्ते, Tamil வணக்கம், Kannada, etc.) using Unicode ranges
  - **AI Intent Detection**: Uses Gemini 2.0 Flash to classify messages as GREETING, QUERY, GRIEVANCE, FOLLOWUP, THANKS
  - **Conversational Responses**: Bot now responds appropriately - answers scheme queries, handles greetings warmly, only registers actual grievances
  - **Language-specific Templates**: Multi-lingual response templates for Telugu, Hindi, Tamil, English
- **10-STEP GRIEVANCE WORKFLOW**: Complete implementation:
  - Step 8a: `PUT /api/grievances/{id}/start-work` - Start Work (changes status to IN_PROGRESS)
  - Step 8b: `PUT /api/grievances/{id}/upload-resolution-photo` - Photo Verification (required)
  - Step 8c: `PUT /api/grievances/{id}/resolve` - Mark Resolved (requires photo first)
  - Step 9: WhatsApp notification to citizen requesting feedback rating
  - Step 10: `PUT /api/grievances/{id}/feedback` - Record 1-5 star rating
- **FRONTEND GRIEVANCE MODAL**: New GrievanceModal component with:
  - Workflow buttons that change based on status (Start Work → Upload Photo → Mark Resolved)
  - Photo verification requirement enforced in UI
  - Real-time status updates and toast notifications

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
