from services.supabase import supabase

async def keep_supabase_alive():
    try:
        # 実在する & 行数の少ないテーブル
        supabase.table("user_vr").select("vr").limit(1).execute()
        print("[keep_alive] Supabase ping OK")
    except Exception as e:
        print(f"[keep_alive] failed: {e}")
