# YOU - Governance ERP & Workflow Automation for Legislators

## Product Overview
A production-ready SaaS platform for Indian political leaders featuring AI-powered governance tools.

## Changelog

### 2026-02-11 (CTO CODE RED - GOLD STANDARD SOLUTION)

**ROOT CAUSE IDENTIFIED:**
```
openai.AuthenticationError: Error code: 401 - Incorrect API key provided: sk-emerg***
```
The **Emergent LLM Key** is NOT a standard OpenAI API key. It only works with the `emergentintegrations` library, NOT with direct OpenAI SDK calls.

**GOLD STANDARD SOLUTION IMPLEMENTED:**

| Component | Previous (Broken) | New (Fixed) |
|-----------|------------------|-------------|
| **Image OCR** | Direct OpenAI SDK with `AsyncOpenAI` | Gemini Vision via `emergentintegrations` |
| **Model** | `gpt-4o` (auth failed) | `gemini-2.0-flash` (working) |
| **Image Format** | `image_url` dict format | `ImageContent(image_base64=...)` |

**Code Changes:**
```python
# OLD (BROKEN) - Direct OpenAI SDK doesn't accept Emergent key
from openai import AsyncOpenAI
client = AsyncOpenAI(api_key=EMERGENT_LLM_KEY)  # ❌ 401 Auth Error

# NEW (WORKING) - Use emergentintegrations with Gemini Vision
from emergentintegrations.llm.chat import ImageContent
image_content = ImageContent(image_base64=media_base64)
chat = LlmChat(api_key=EMERGENT_LLM_KEY, ...).with_model("gemini", "gemini-2.0-flash")
msg = UserMessage(text=prompt, file_contents=[image_content])
result = await chat.send_message(msg)  # ✅ Works!
```

**Test Results:**
```
✅ PNG Image OCR: Name=Rahul Kumar, Phone=9876543210, Category=Infrastructure & Roads
✅ JPEG Image OCR: Name=Mohan Singh, Phone=8765432109, Category=Water & Irrigation
✅ /api/ai/extract_from_media - Working
✅ /api/ai/analyze_image - Working
✅ /api/grievances/analyze-grievance - Working
```

**Files Updated:**
- `backend/routes/ai_routes.py`:
  - `extract_grievance_from_media()` - Now uses Gemini Vision with ImageContent
  - `process_image_with_vision()` - Now uses Gemini Vision with ImageContent
  - Both functions log with `[GOLD STANDARD OCR]` prefix

**Bot Version:** 4.0 - Holistic Knowledge + Gemini Vision

### Previous Updates
- 2026-02-11: FFmpeg installed, Hinglish detection added, language consistency fixed
- 2026-02-06: OSD Persona v3.5 with Iron Dome language protection

## Tech Stack
- **Frontend**: React + TailwindCSS + Recharts + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **AI Vision**: **Gemini 2.0 Flash** via Emergent LLM Key
- **AI Text**: GPT-4o-mini via Emergent LLM Key
- **Audio**: OpenAI Whisper-1 via emergentintegrations
- **Messaging**: Twilio WhatsApp API
- **Media Processing**: FFmpeg for audio conversion

## Key API Endpoints

### AI Routes (Image Processing)
- `POST /api/ai/extract_from_media` - OCR extraction from image/PDF
- `POST /api/ai/analyze_image` - Dedicated image analysis
- `POST /api/grievances/analyze-grievance` - Grievance file analysis

### AI Routes (Text/Voice)
- `POST /api/ai/analyze_intent` - OSD Brain with language-aware responses
- `POST /api/ai/transcribe` - Audio transcription (OGG, WebM, MP3)

## Test Credentials
- Email: `ramkumar@example.com`
- Password: `test123`

## Pending User Verification
- [ ] **WhatsApp Voice Note**: Send a voice note to verify transcription
- [ ] **WhatsApp Image**: Send a document image to verify WhatsApp OCR path

## Completed Tasks
- [x] **Image OCR (GOLD STANDARD)** - Using Gemini Vision via emergentintegrations
- [x] Voice transcription fix (FFmpeg installed)
- [x] Language detection fix (Hinglish support added)
- [x] English response for English input
- [x] All image processing endpoints working
