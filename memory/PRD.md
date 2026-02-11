# YOU - Governance ERP & Workflow Automation for Legislators

## Product Overview
A production-ready SaaS platform for Indian political leaders featuring AI-powered governance tools.

## Changelog

### 2026-02-11 (CTO-Approved Message Templates)

**NEW FEATURES:**

#### 1. Warm Greeting Message
```
Namaste, [Name].
Thank you for reaching out to the Office of the Leader. We truly appreciate 
you taking the time to connect with us.

We are here to support you. You may share your query or register a grievance, 
and our team will carefully look into the matter and assist you as soon as possible.
```

#### 2. Grievance Registration Confirmation
```
Your grievance has been successfully registered. Please find the details below:

📋 Issue Category: [Category]
📝 Issue Type: [Description]
🎫 Ticket Number: #[TicketID]

Thank you for bringing this to our attention. We understand that your concern 
is important, and our team will review it with care.

Please stay connected for updates. We are committed to keeping you informed 
throughout the process.
```

**Implementation:**
- `whatsapp_routes.py`: Added `get_osd_response()` with greeting template
- `whatsapp_routes.py`: Added `get_grievance_confirmation_message()` function
- `ai_routes.py`: Updated system prompt to use warm greeting for CHAT intents
- Messages are automatically translated to user's detected language

**Bot Version:** 4.2 - CTO-Approved Warm Messages

### Previous Updates (2026-02-11)
- Gold Standard OCR with Gemini Vision
- PDF processing with PyMuPDF
- Language safety (no foreign languages)
- FFmpeg for voice transcription

## Message Templates

### Greeting (CHAT Intent)
| Language | Response |
|----------|----------|
| English | Namaste, [Name]. Thank you for reaching out... |
| Hindi | नमस्ते, [Name]. नेता के कार्यालय से संपर्क करने के लिए धन्यवाद... |
| Hinglish | Namaste, [Name]. Leader ke office se contact karne ke liye dhanyawad... |

### Grievance Confirmation
| Field | Example |
|-------|---------|
| Category | Infrastructure & Roads |
| Issue Type | Road is broken near village... |
| Ticket Number | #ABC12345 |

## Tech Stack
- **Frontend**: React + TailwindCSS + Shadcn UI
- **Backend**: FastAPI (Python)
- **Database**: Supabase (PostgreSQL)
- **AI Vision**: Gemini 2.0 Flash (via Emergent LLM Key)
- **AI Text**: GPT-4o-mini (via Emergent LLM Key)
- **PDF Processing**: PyMuPDF
- **Audio**: OpenAI Whisper-1

## Language Support
| Code | Language | Script |
|------|----------|--------|
| en | English | Roman |
| hi | Hindi | Devanagari |
| hinglish | Hindi | Roman |
| te | Telugu | Telugu |
| tenglish | Telugu | Roman |
| ta | Tamil | Tamil |
| kn | Kannada | Kannada |
| ml | Malayalam | Malayalam |
| bn | Bengali | Bengali |
| mr | Marathi | Devanagari |
| gu | Gujarati | Gujarati |
| pa | Punjabi | Gurmukhi |

## Test Credentials
- Email: `ramkumar@example.com`
- Password: `test123`

## Completed Tasks
- [x] Warm greeting message (CTO-approved)
- [x] Grievance confirmation template
- [x] Language translation for all messages
- [x] Foreign language safety check
- [x] PDF OCR with PyMuPDF
- [x] Image OCR with Gemini Vision
