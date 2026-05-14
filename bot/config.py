import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DATABASE_URL = os.getenv("DATABASE_URL")

if not BOT_TOKEN:
    raise ValueError("Missing BOT_TOKEN environment variable.")

if not DATABASE_URL and not all([SUPABASE_URL, SUPABASE_KEY]):
    raise ValueError("Missing database config. Set DATABASE_URL or SUPABASE_URL + SUPABASE_ANON_KEY.")
