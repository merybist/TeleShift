from supabase import create_client, Client
from config import SUPABASE_URL, SUPABASE_KEY

sb: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
