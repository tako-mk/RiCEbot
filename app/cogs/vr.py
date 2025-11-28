import discord
from discord import app_commands
from discord.ext import commands
import os
import json
from supabase import create_client

DATABASE_URL = os.getenv("DATABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # 公開用APIキーかサービスキー
supabase = create_client(DATABASE_URL, SUPABASE_KEY)

HOUR_JSON = os.path.join(os.path.dirname(__file__), "..", "hours.json")

def load_hours():
    if not os.path.exists(HOUR_JSON):
        return {}
    with open(HOUR_JSON, "r", encoding="utf-8") as f:
        return json.load(f)

class VR(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="vr")
    async def set_vr(self, interaction: discord.Interaction, value: int):
        """自分の VR を登録、すでにある場合は表示"""
        user_id = interaction.user.id

        # まず既存の値を取得
        existing = supabase.table("user_vr").select("vr").eq("user_id", user_id).execute()
        if existing.data:
            current_vr = existing.data[0]["vr"]
            await interaction.response.send_message(
                f"{interaction.user.mention} はすでに VR {current_vr} が登録されています。", ephemeral=True
            )
            return

        # 登録
        supabase.table("user_vr").upsert({"user_id": user_id, "vr": value}).execute()
        await interaction.response.send_message(
            f"{interaction.user.mention} の VR を {value} に登録しました。", ephemeral=True
        )

    @app_commands.command(name="ave")
    async def ave_vr(self, interaction: discord.Interaction, hour: str):
        """指定 hour のメンバーの VR 平均を表示"""
        hours = load_hours()
        if hour not in hours:
            await interaction.response.send_message("その hour は存在しません。", ephemeral=True)
            return

        role_id = hours[hour]
        role = interaction.guild.get_role(role_id)
        if not role:
            await interaction.response.send_message("ロールが存在しません。", ephemeral=True)
            return

        user_ids = [m.id for m in role.members]
        if not user_ids:
            await interaction.response.send_message("その hour に登録されているメンバーはいません。", ephemeral=True)
            return

        data = supabase.table("user_vr").select("user_id, vr").in_("user_id", user_ids).execute()
        records = data.data
        if not records:
            await interaction.response.send_message("その hour に VR が登録されているメンバーはいません。", ephemeral=True)
            return

        vr_list = [r["vr"] for r in records]
        avg = sum(vr_list) / len(vr_list)
        await interaction.response.send_message(f"{hour} 時の VR 平均: {avg:.2f}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(VR(bot))
