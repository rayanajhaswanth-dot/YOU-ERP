# YOU - Governance ERP & Workflow Automation for Legislators

## Product Overview
A production-ready SaaS platform for Indian political leaders featuring AI-powered governance tools.

## Changelog

### 2026-02-11 (CTO CODE RED - Critical Bug Fixes)

**ROOT CAUSE ANALYSIS:**

| Issue | Root Cause | Fix Applied |
|-------|------------|-------------|
| **Voice Note Failure** | FFmpeg not installed + Whisper API doesn't support OGG format | ✅ Installed FFmpeg, code converts OGG→MP3 before transcription |
| **Image Processing Failure** | LiteLLM wrapper rejecting image MIME types | ✅ Switched to direct OpenAI SDK for Vision API calls |
| **Language Inconsistency** | `detect_language()` only detected Indic scripts, not Hinglish | ✅ Added Hinglish keyword detection |

**Critical Fixes Implemented:**

#### 1. Voice Transcription (FIXED)
- **Problem**: `[Errno 2] No such file or directory: 'ffmpeg'` and `Unsupported file format: ogg`
- **Fix**: 
  - Installed FFmpeg: `apt-get install ffmpeg`
  - Code converts OGG/OPUS → MP3 before sending to Whisper
  - File: `ai_routes.py` - `transcribe_audio()` function

#### 2. Image/Document OCR (FIXED)
- **Problem**: `Invalid file data... Expected application/pdf MIME type... but got unsupported MIME type 'image/jpeg'`
- **Fix**: 
  - Replaced LlmChat FileContent with direct OpenAI AsyncClient
  - Uses proper `image_url` format: `data:image/jpeg;base64,{base64_data}`
  - File: `ai_routes.py` - `extract_grievance_from_media()` function

#### 3. Language Consistency (FIXED)
- **Problem**: Bot responding in Hindi when user writes in English
- **Fix**:
  - Added Hinglish keyword detection (mera, nahi, kya, hai, etc.)
  - System prompt now explicitly instructs: "If detected_lang is 'en' → Reply ONLY in English"
  - Language is passed directly to the prompt: `CURRENT USER'S LANGUAGE: {detected_lang}`
  - File: `ai_routes.py` - `detect_language()` and `analyze_incoming_message()`

**Test Results:**
- ✅ English input → English response
- ✅ Hinglish input → Hinglish response  
- ✅ Hindi (Devanagari) input → Hindi response
- ✅ FFmpeg installed and working
- ✅ Vision API using correct format

**Bot Version:** 4.0 - Holistic Knowledge + Vision Analysis

### Previous Updates
- 2026-02-11: Draconian OSD Prompt, safeFetch wrapper, file input fixes
- 2026-02-06: OSD Persona v3.5 with Iron Dome language protection
- 2026-02-06: CTO Mandate - Media extraction, language detection, category normalization

## Tech Stack
- **Frontend**: React + TailwindCSS + Recharts + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **AI**: OpenAI GPT-4o/GPT-4o-mini (via Emergent LLM Key), Whisper for voice
- **Messaging**: Twilio WhatsApp API
- **Media Processing**: FFmpeg for audio conversion

## Key API Endpoints

### AI Routes
- `POST /api/ai/analyze_intent` - OSD Brain with language-aware responses
- `POST /api/ai/transcribe` - Audio transcription (OGG, WebM, MP3)
- `POST /api/ai/extract_from_media` - Image/PDF OCR extraction

### WhatsApp Routes
- `POST /api/whatsapp/webhook` - Main webhook (handles text, voice, image)
- `GET /api/whatsapp/status` - Version 4.0 status

## Language Detection Logic
```
1. Check for Indic scripts (Devanagari, Telugu, Tamil, etc.)
2. If Roman script, check for Hinglish keywords
3. Default to English
```

## Test Credentials
- Email: `ramkumar@example.com`
- Password: `test123`

## Pending User Verification
- [ ] **Voice Note**: Send a voice note via WhatsApp to verify transcription works
- [ ] **Image OCR**: Send a handwritten document via WhatsApp to verify OCR works

## Completed Tasks
- [x] Voice transcription fix (FFmpeg + format conversion)
- [x] Image OCR fix (Direct OpenAI Vision API)
- [x] Language detection fix (Hinglish support)
- [x] English response for English input
- [x] Holistic Knowledge system
- [x] safeFetch wrapper for frontend
