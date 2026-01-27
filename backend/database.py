from supabase import create_client, Client
import os
from dotenv import load_dotenv
from pathlib import Path

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

supabase_url = os.environ.get('SUPABASE_URL')
# Use SERVICE_KEY to bypass RLS policies for backend operations
supabase_key = os.environ.get('SUPABASE_SERVICE_KEY') or os.environ.get('SUPABASE_ANON_KEY')

supabase: Client = create_client(supabase_url, supabase_key)

def get_supabase() -> Client:
    return supabase