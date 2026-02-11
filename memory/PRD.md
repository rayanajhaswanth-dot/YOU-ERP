# YOU - Governance ERP & Workflow Automation for Legislators

## Product Overview
A production-ready SaaS platform for Indian political leaders featuring AI-powered governance tools.

## Changelog

### 2026-02-11 (CTO CODE RED - P0 Complete)

**Critical Fixes Implemented:**

#### A. "Draconian OSD" System Prompt (Language Enforcement)
- ✅ Updated `ai_routes.py` with strict formal language enforcement
- ✅ AI now responds FORMALLY even to casual Hindi ("need food bhai" → formal bureaucratic response)
- ✅ Token disambiguation: Tu/Mera/De/Se/Me → Hindi (NOT French/Spanish)
- ✅ Absolutely forbidden: French, Spanish, German, Portuguese
- ✅ Examples of correct vs incorrect responses built into prompt

#### B. Holistic Knowledge System
- ✅ AI retrieves official `.gov.in` URLs for ANY Indian government scheme
- ✅ Covers all 28 states + 8 Union Territories
- ✅ National schemes: PM Kisan, PMJAY, PMAY, Aadhaar, etc.
- ✅ State-specific schemes: Ladli Behna (MP), Aarogyasri (TS/AP), etc.
- ✅ Knowledge retrieval from AI's internal training data

#### C. Image Processing with GPT-4o Vision
- ✅ New `/api/ai/analyze_image` endpoint for image-based grievance analysis
- ✅ `process_image_with_vision()` function for enhanced OCR
- ✅ Automatic category detection from image content
- ✅ Supports JPG, PNG images of damaged infrastructure, documents, etc.

#### D. Voice Transcription Enhancement
- ✅ `/api/ai/transcribe` now accepts both 'file' and 'audio' form field names
- ✅ `/api/ai/transcribe-audio` dedicated endpoint for web frontend
- ✅ Returns detected language name (Telugu, Hindi, Tamil, etc.)
- ✅ Returns English translation for non-English audio

#### E. Frontend safeFetch Wrapper
- ✅ Created `/app/frontend/src/utils/safeFetch.js`
- ✅ Prevents "body stream already used" errors
- ✅ Automatic JSON/text response handling
- ✅ Token injection and error handling
- ✅ Updated `HelpPeople.jsx` to use safeFetch throughout

#### F. File Upload Enhancement
- ✅ File input now explicitly accepts `.jpg`, `.jpeg`, `.png`, `application/pdf`
- ✅ Updated UI text to show "JPG, PNG, PDF" formats

#### G. Database Schema Compatibility Fix
- ✅ Fixed `resolved_at` column error in resolve endpoint
- ✅ Graceful fallback if column doesn't exist in schema

**Files Updated:**
- `backend/routes/ai_routes.py` - Draconian prompt, transcribe endpoints, vision processing
- `backend/routes/grievance_routes.py` - analyze-grievance endpoint, schema fix
- `backend/routes/whatsapp_routes.py` - Version 4.0 status
- `frontend/src/utils/safeFetch.js` - NEW: Robust fetch wrapper
- `frontend/src/pages/HelpPeople.jsx` - Using safeFetch, file input fix

**WhatsApp Bot Version:** 4.0 - Holistic Knowledge + Vision Analysis

### Previous Updates
- 2026-02-06: OSD Persona v3.5 with Iron Dome language protection
- 2026-02-06: CTO Mandate - Media extraction, language detection, category normalization
- 2026-02-04: File upload from device, voice transcription fixes

## Tech Stack
- **Frontend**: React + TailwindCSS + Recharts + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **AI**: OpenAI GPT-4o/GPT-4o-mini (via Emergent LLM Key), Whisper for voice
- **Messaging**: Twilio WhatsApp API

## Key API Endpoints

### AI Routes
- `POST /api/ai/analyze_intent` - OSD Brain with Holistic Knowledge
- `POST /api/ai/transcribe` - Audio transcription (accepts 'file' or 'audio')
- `POST /api/ai/transcribe-audio` - Dedicated web frontend transcription
- `POST /api/ai/analyze_image` - GPT-4o Vision image analysis
- `POST /api/ai/extract_from_media` - PDF/Image OCR extraction

### Grievance Routes
- `GET /api/grievances/` - List all grievances
- `POST /api/grievances/` - Create grievance
- `DELETE /api/grievances/{id}` - Delete grievance
- `POST /api/grievances/analyze-grievance` - AI-powered file analysis
- `PUT /api/grievances/{id}/resolve` - Mark resolved (with schema compatibility)

### WhatsApp Routes
- `POST /api/whatsapp/webhook` - Main webhook
- `GET /api/whatsapp/status` - Version 4.0 status

## Test Credentials
- Email: `ramkumar@example.com`
- Password: `test123`

## Pending Tasks
- [ ] **P1: Verify Voice Transcription Live** - User needs to send WhatsApp voice note
- [ ] **P1: Refine Broadcast Center** - View past broadcast history
- [ ] **P2: Expand RBAC** - Cover more UI components
- [ ] **P3: Real-time WebSocket ticker**

## Completed Tasks
- [x] **P0: CTO Code Red Update** - All critical fixes implemented
- [x] Draconian formal language enforcement
- [x] Holistic Knowledge system for ANY government scheme
- [x] GPT-4o Vision image processing
- [x] safeFetch wrapper for frontend
- [x] File input explicit format acceptance
- [x] Database schema compatibility fix
