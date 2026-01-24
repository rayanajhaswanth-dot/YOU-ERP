# YOU - Governance ERP & Workflow Automation

A production-ready SaaS platform for Indian political leaders to manage millions of constituents via AI automation, real-time grievance tracking, and cross-platform communication.

## Features

### 🏠 Briefing Room (Dashboard)
- Live feed with real-time activity updates
- AI-generated constituency overview using Gemini
- Campaign suggestions based on recurring grievances
- Weekly activity charts and statistics

### 👥 Help People (Grievance Management)
- Grievance registration with AI-powered triage
- Priority scoring (1-10) using Gemini AI
- Status tracking (Pending → In Progress → Resolved)
- WhatsApp bot framework (ready for Twilio credentials)
- Letter OCR framework (ready for implementation)

### 📢 Send News (Broadcast Center)
- Multi-platform post creation (WhatsApp, X/Twitter, Instagram, Facebook)
- AI post polishing using Gemini
- Approval workflow (OSD drafts → Politician approves)
- Scheduled posts support

### ❤️ Happiness Report (Sentiment Analytics)
- Real-time sentiment tracking
- Sentiment trend analysis with charts
- Issue distribution visualization
- Platform-wise mention tracking
- Social listening framework

## Tech Stack

- **Frontend**: React 19, Tailwind CSS, Framer Motion, Recharts, Lucide Icons
- **Backend**: FastAPI (Python), Supabase (PostgreSQL)
- **AI**: Google Gemini (via Emergent LLM Key)
- **Theme**: Executive Saffron (Slate-900 bg, Orange-500 accents, 2.5rem border-radius)

## Setup Instructions

### 1. Supabase Database Setup

Run these SQL commands in your Supabase SQL Editor:

```sql
-- Politicians table
CREATE TABLE politicians (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    constituency TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('politician', 'osd', 'pa')),
    politician_id UUID REFERENCES politicians(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Grievances table
CREATE TABLE grievances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    politician_id UUID REFERENCES politicians(id),
    constituent_name TEXT NOT NULL,
    phone TEXT NOT NULL,
    message TEXT NOT NULL,
    source TEXT DEFAULT 'whatsapp',
    priority INTEGER DEFAULT 5,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'in_progress', 'resolved')),
    resolution_notes TEXT,
    assigned_to UUID REFERENCES users(id),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- Posts table
CREATE TABLE posts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    politician_id UUID REFERENCES politicians(id),
    content TEXT NOT NULL,
    platforms TEXT[] NOT NULL,
    status TEXT DEFAULT 'draft' CHECK (status IN ('draft', 'approved', 'published')),
    scheduled_at TIMESTAMPTZ,
    created_by UUID REFERENCES users(id),
    approved_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    approved_at TIMESTAMPTZ,
    published_at TIMESTAMPTZ
);

-- Sentiment analytics table
CREATE TABLE sentiment_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    politician_id UUID REFERENCES politicians(id),
    platform TEXT NOT NULL,
    sentiment_score FLOAT NOT NULL,
    issue_category TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);
```

### 2. Seed Demo Data

```bash
cd /app/backend
python seed_supabase.py
```

### 3. Access the Application

- Frontend: http://localhost:3000
- Backend API: http://localhost:8001/api

### 4. Demo Credentials

- **Politician**: politician@demo.com / password123
- **OSD (Manager)**: osd@demo.com / password123
- **PA (Scheduler)**: pa@demo.com / password123

## Demo Credentials
- **Politician**: politician@demo.com / password123
- **OSD (Manager)**: osd@demo.com / password123
- **PA (Scheduler)**: pa@demo.com / password123
