from supabase import create_client
import os

supabase = create_client(
    os.getenv("DATABASE_URL"),
    os.getenv("SUPABASE_KEY")
)
