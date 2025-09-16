# utils/supabase_client.py
import os
from supabase import create_client, Client

_supabase: Client | None = None

def supabase() -> Client:
    global _supabase
    if _supabase is None:
        url = os.environ["SUPABASE_URL"]
        key = os.environ["SUPABASE_SERVICE_ROLE_KEY"]  # server-side
        _supabase = create_client(url, key)
    return _supabase
