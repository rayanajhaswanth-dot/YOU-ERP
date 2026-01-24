"""
Seed script for Supabase tables
Run this to create demo data in your Supabase database

Instructions:
1. First, create these tables in Supabase SQL Editor:

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

2. Then run this script: python seed_supabase.py
"""

import os
from dotenv import load_dotenv
from pathlib import Path
from database import get_supabase
from auth import get_password_hash
import uuid

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

def seed_data():
    supabase = get_supabase()
    
    print("🌱 Seeding Supabase database...")
    
    # Create politician
    politician_id = str(uuid.uuid4())
    politician_data = {
        'id': politician_id,
        'name': 'Rajesh Kumar',
        'constituency': 'South Delhi',
        'state': 'Delhi'
    }
    
    try:
        supabase.table('politicians').insert(politician_data).execute()
        print(f"✅ Created politician: {politician_data['name']}")
    except Exception as e:
        print(f"⚠️  Politician may already exist: {e}")
    
    # Create demo users
    users_data = [
        {
            'id': str(uuid.uuid4()),
            'email': 'politician@demo.com',
            'password_hash': get_password_hash('password123'),
            'full_name': 'Rajesh Kumar',
            'role': 'politician',
            'politician_id': politician_id
        },
        {
            'id': str(uuid.uuid4()),
            'email': 'osd@demo.com',
            'password_hash': get_password_hash('password123'),
            'full_name': 'Priya Sharma',
            'role': 'osd',
            'politician_id': politician_id
        },
        {
            'id': str(uuid.uuid4()),
            'email': 'pa@demo.com',
            'password_hash': get_password_hash('password123'),
            'full_name': 'Amit Verma',
            'role': 'pa',
            'politician_id': politician_id
        }
    ]
    
    for user in users_data:
        try:
            supabase.table('users').insert(user).execute()
            print(f"✅ Created user: {user['email']} ({user['role']})")
        except Exception as e:
            print(f"⚠️  User may already exist: {user['email']}")
    
    # Create sample grievances
    sample_grievances = [
        {
            'id': str(uuid.uuid4()),
            'politician_id': politician_id,
            'constituent_name': 'Sunita Devi',
            'phone': '+91 9876543210',
            'message': 'Water supply has been irregular in our area for the past week. Need immediate attention.',
            'source': 'whatsapp',
            'priority': 8,
            'status': 'pending',
            'created_by': users_data[0]['id']
        },
        {
            'id': str(uuid.uuid4()),
            'politician_id': politician_id,
            'constituent_name': 'Ramesh Gupta',
            'phone': '+91 9876543211',
            'message': 'Street lights not working in Sector 15. Safety concern for residents.',
            'source': 'manual',
            'priority': 6,
            'status': 'in_progress',
            'created_by': users_data[1]['id']
        },
        {
            'id': str(uuid.uuid4()),
            'politician_id': politician_id,
            'constituent_name': 'Kavita Singh',
            'phone': '+91 9876543212',
            'message': 'Need assistance with Ayushman Bharat card application. Documents submitted but no response.',
            'source': 'whatsapp',
            'priority': 5,
            'status': 'resolved',
            'created_by': users_data[2]['id']
        }
    ]
    
    for grievance in sample_grievances:
        try:
            supabase.table('grievances').insert(grievance).execute()
            print(f"✅ Created grievance from: {grievance['constituent_name']}")
        except Exception as e:
            print(f"⚠️  Grievance may already exist")
    
    # Create sample posts
    sample_posts = [
        {
            'id': str(uuid.uuid4()),
            'politician_id': politician_id,
            'content': 'Proud to announce the completion of road reconstruction in Sector 12. Better infrastructure for our community!',
            'platforms': ['twitter', 'facebook', 'whatsapp'],
            'status': 'published',
            'created_by': users_data[1]['id'],
            'approved_by': users_data[0]['id']
        },
        {
            'id': str(uuid.uuid4()),
            'politician_id': politician_id,
            'content': 'Upcoming town hall meeting on Saturday at 4 PM. Looking forward to hearing from you all!',
            'platforms': ['instagram', 'facebook'],
            'status': 'draft',
            'created_by': users_data[2]['id']
        }
    ]
    
    for post in sample_posts:
        try:
            supabase.table('posts').insert(post).execute()
            print(f"✅ Created post with status: {post['status']}")
        except Exception as e:
            print(f"⚠️  Post may already exist")
    
    # Create sample sentiment data
    sample_sentiment = [
        {
            'id': str(uuid.uuid4()),
            'politician_id': politician_id,
            'platform': 'twitter',
            'sentiment_score': 0.8,
            'issue_category': 'Infrastructure',
            'content': 'Great work on the new road! Much needed improvement.'
        },
        {
            'id': str(uuid.uuid4()),
            'politician_id': politician_id,
            'platform': 'facebook',
            'sentiment_score': 0.3,
            'issue_category': 'Water Supply',
            'content': 'When will the water supply issue be fixed? Been waiting for days.'
        }
    ]
    
    for sentiment in sample_sentiment:
        try:
            supabase.table('sentiment_analytics').insert(sentiment).execute()
            print(f"✅ Created sentiment entry for: {sentiment['issue_category']}")
        except Exception as e:
            print(f"⚠️  Sentiment may already exist")
    
    print("\n✨ Seeding complete!")
    print("\n📝 Demo credentials:")
    print("   Email: politician@demo.com")
    print("   Email: osd@demo.com")
    print("   Email: pa@demo.com")
    print("   Password: password123")

if __name__ == "__main__":
    seed_data()
