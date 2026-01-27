-- YOU - Governance ERP Supabase Schema
-- Run this in your Supabase SQL Editor before running the seed script

-- Politicians table
CREATE TABLE IF NOT EXISTS politicians (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    constituency TEXT NOT NULL,
    state TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('politician', 'osd', 'pa')),
    politician_id UUID REFERENCES politicians(id),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Grievances table (Updated with AI Reality Matrix fields)
CREATE TABLE IF NOT EXISTS grievances (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    politician_id UUID REFERENCES politicians(id),
    constituent_name TEXT DEFAULT 'Anonymous Citizen',
    phone TEXT,
    village TEXT DEFAULT 'Unknown',
    description TEXT NOT NULL,
    message TEXT,
    source TEXT DEFAULT 'whatsapp',
    
    -- AI Reality Matrix Fields
    priority_level TEXT DEFAULT 'LOW' CHECK (priority_level IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    deadline_timestamp TIMESTAMPTZ,
    issue_type TEXT DEFAULT 'Other',
    ai_priority INTEGER DEFAULT 5,
    media_url TEXT,
    
    -- Legacy/Compatibility
    priority INTEGER DEFAULT 5,
    status TEXT DEFAULT 'PENDING' CHECK (status IN ('PENDING', 'IN_PROGRESS', 'RESOLVED', 'pending', 'in_progress', 'resolved')),
    resolution_notes TEXT,
    assigned_to UUID REFERENCES users(id),
    created_by UUID REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

-- Migration: Add new columns if table already exists (run these if upgrading)
-- ALTER TABLE grievances ADD COLUMN IF NOT EXISTS priority_level TEXT DEFAULT 'LOW';
-- ALTER TABLE grievances ADD COLUMN IF NOT EXISTS deadline_timestamp TIMESTAMPTZ;
-- ALTER TABLE grievances ADD COLUMN IF NOT EXISTS issue_type TEXT DEFAULT 'Other';
-- ALTER TABLE grievances ADD COLUMN IF NOT EXISTS ai_priority INTEGER DEFAULT 5;
-- ALTER TABLE grievances ADD COLUMN IF NOT EXISTS media_url TEXT;
-- ALTER TABLE grievances ADD COLUMN IF NOT EXISTS village TEXT DEFAULT 'Unknown';
-- ALTER TABLE grievances ADD COLUMN IF NOT EXISTS description TEXT;

-- Posts table
CREATE TABLE IF NOT EXISTS posts (
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
CREATE TABLE IF NOT EXISTS sentiment_analytics (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    politician_id UUID REFERENCES politicians(id),
    platform TEXT NOT NULL,
    sentiment_score FLOAT NOT NULL,
    issue_category TEXT NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_users_politician_id ON users(politician_id);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_grievances_politician_id ON grievances(politician_id);
CREATE INDEX IF NOT EXISTS idx_grievances_status ON grievances(status);
CREATE INDEX IF NOT EXISTS idx_posts_politician_id ON posts(politician_id);
CREATE INDEX IF NOT EXISTS idx_posts_status ON posts(status);
CREATE INDEX IF NOT EXISTS idx_sentiment_politician_id ON sentiment_analytics(politician_id);

-- Row Level Security (RLS) Policies
-- Enable RLS on all tables
ALTER TABLE politicians ENABLE ROW LEVEL SECURITY;
ALTER TABLE users ENABLE ROW LEVEL SECURITY;
ALTER TABLE grievances ENABLE ROW LEVEL SECURITY;
ALTER TABLE posts ENABLE ROW LEVEL SECURITY;
ALTER TABLE sentiment_analytics ENABLE ROW LEVEL SECURITY;

-- RLS Policies: Allow all operations for now (you can restrict based on your needs)
-- Politicians
CREATE POLICY IF NOT EXISTS "Allow all operations on politicians" ON politicians FOR ALL USING (true);

-- Users
CREATE POLICY IF NOT EXISTS "Allow all operations on users" ON users FOR ALL USING (true);

-- Grievances
CREATE POLICY IF NOT EXISTS "Allow all operations on grievances" ON grievances FOR ALL USING (true);

-- Posts
CREATE POLICY IF NOT EXISTS "Allow all operations on posts" ON posts FOR ALL USING (true);

-- Sentiment Analytics
CREATE POLICY IF NOT EXISTS "Allow all operations on sentiment_analytics" ON sentiment_analytics FOR ALL USING (true);
