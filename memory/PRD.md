# YOU - Governance ERP & Workflow Automation for Legislators

## Product Overview
A production-ready SaaS platform for Indian political leaders featuring AI-powered governance tools.

## Changelog

### 2026-02-11 (CTO CODE RED - GOLD STANDARD FINAL FIX)

**ISSUES FIXED:**

| Issue | Root Cause | Fix |
|-------|-----------|-----|
| **Foreign Language Response (Romanian)** | `translate_text()` accepting unknown language codes | ✅ Added strict validation + foreign language safety check |
| **PDF Processing Fails** | Gemini Vision doesn't support PDF directly | ✅ Installed PyMuPDF to convert PDF to PNG first |
| **Language Code Validation** | Unknown codes like "unknown_lang" passed through | ✅ Whitelist of valid Indian languages |

**GOLD STANDARD SOLUTIONS:**

#### 1. Translation with Safety Check
```python
# Only translate to KNOWN Indian languages
VALID_LANGUAGES = ['en', 'hi', 'hinglish', 'te', 'tenglish', 'ta', 'kn', 'ml', 'bn', 'mr', 'gu', 'pa']

# If unknown language, default to English
if language not in VALID_LANGUAGES:
    language = 'en'

# After translation, check for foreign language markers
foreign_markers = ['constatat', 'nemulțumirea', 'înregistrat', ...]  # Romanian
if any(marker in response.lower() for marker in foreign_markers):
    return english_text  # Safety fallback
```

#### 2. PDF Processing with PyMuPDF
```python
import fitz  # PyMuPDF
pdf_doc = fitz.open(stream=media_data, filetype="pdf")
page = pdf_doc[0]
pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better OCR
image_data = pix.tobytes("png")
# Then process image_data with Gemini Vision
```

#### 3. All Output in English for Database
- All grievances stored in English
- Category: Official English category only
- Description: English (translated/summarized)
- Name/Area: Transliterated to English

**Test Results:**
```
✅ Image OCR → English description
✅ PDF Processing → PyMuPDF conversion → Gemini OCR → English output
✅ Hindi translation → Correct Hindi (not Romanian)
✅ Unknown language → Falls back to English
✅ Foreign language detection → Safety check blocks and returns English
```

**Files Updated:**
- `backend/routes/ai_routes.py`:
  - `translate_text()` - Added VALID_LANGUAGES whitelist + foreign marker check
  - `extract_grievance_from_media()` - Added PyMuPDF PDF conversion
  - `process_image_with_vision()` - Returns valid language codes only
- `backend/routes/whatsapp_routes.py`:
  - `register_grievance_osd()` - Validates language before translation

**Dependencies Added:**
- PyMuPDF (`pip install PyMuPDF`)
- reportlab (for PDF testing)

**Bot Version:** 4.1 - Gold Standard Language + PDF Support

### Previous Updates
- 2026-02-11: Gemini Vision OCR, FFmpeg installed, Hinglish detection
- 2026-02-06: OSD Persona v3.5 with Iron Dome language protection

## Tech Stack
- **Frontend**: React + TailwindCSS + Recharts + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **AI Vision**: Gemini 2.0 Flash via Emergent LLM Key
- **PDF Processing**: PyMuPDF (converts PDF to image for OCR)
- **Audio**: OpenAI Whisper-1 via emergentintegrations
- **Messaging**: Twilio WhatsApp API

## Language Handling

### Valid Language Codes
| Code | Language |
|------|----------|
| en | English |
| hi | Hindi (Devanagari) |
| hinglish | Hindi (Roman script) |
| te | Telugu |
| tenglish | Telugu (Roman script) |
| ta | Tamil |
| kn | Kannada |
| ml | Malayalam |
| bn | Bengali |
| mr | Marathi |
| gu | Gujarati |
| pa | Punjabi |

### Language Flow
1. **OCR**: Detects original language, outputs English
2. **Database**: Stores language code + English description
3. **Response**: Translates confirmation to user's language (if valid)
4. **Fallback**: Unknown languages → English response

## Test Credentials
- Email: `ramkumar@example.com`
- Password: `test123`

## Completed Tasks
- [x] Foreign language bug fixed (Romanian issue)
- [x] PDF processing fixed (PyMuPDF conversion)
- [x] All outputs in English for database
- [x] Valid language code validation
- [x] Safety check for translation output
