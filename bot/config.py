import os
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
BOT_TOKEN = os.getenv("BOT_TOKEN")

if not all([SUPABASE_URL, SUPABASE_KEY, BOT_TOKEN]):
    raise ValueError("Missing essential environment variables.")
