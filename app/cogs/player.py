import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import statistics
from services.supabase import supabase

from services.lounge_api import fetch_mmr
from services.lounge_api import fetch_peak

# プレイヤーデータに関するコマンド
class Player(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # ラウンジデータ取得・Embed作成関数
    async def _average_mmr_command(
        self,
        interaction: discord.Interaction,
        role: discord.Role,
        fetch_func,
        title_suffix: str
    ):
        await interaction.response.defer()

        members = [m for m in role.members if not m.bot]
        if not members:
            await interaction.followup.send("そのロールにメンバーがいません。")
            return

        results = await asyncio.gather(
            *[fetch_func(m.id) for m in members]
        )

        values = []
        lines = []
        skipped = 0

        for member, value in zip(members, results):
            if value is None:
                skipped += 1
                continue
            values.append(value)
            lines.append(f"{member.display_name}: **{value}**")

        if not values:
            await interaction.followup.send("取得できるデータがありません。")
            return

        avg = int(statistics.mean(values))

        embed = discord.Embed(
            title=f"{role.name} の{title_suffix}",
            description="\n".join(lines[:20]),
            color=discord.Color.blue()
        )
        embed.add_field(name="平均", value=f"**{avg}**", inline=False)
        embed.set_footer(text=f"{len(values)}人分 | placement {skipped}人")

        await interaction.followup.send(embed=embed)

    # /avemmr role:○○
    @app_commands.command(name="avemmr")
    async def avemmr(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        """mmrリスト・平均の表示"""
        await self._average_mmr_command(
            interaction, role, fetch_mmr, "MMR"
        )

    # /avepeak role:○○
    @app_commands.command(name="avepeak")
    async def avepeak(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        """peakmmrリスト・平均の表示"""
        await self._average_mmr_command(
            interaction, role, fetch_peak, "Peak MMR"
        )

    # /vr_register vr:○○
    @app_commands.command(name="vr_register")
    @app_commands.describe(vr="VR（半角数字）")
    async def vr_register(
        self,
        interaction: discord.Interaction,
        vr: str
    ):
        """自分のVRを登録・更新します"""

        # 半角数字チェック
        if not vr.isdigit():
            await interaction.response.send_message(
                "VRは半角数字で入力してください。",
                ephemeral=True
            )
            return

        user_id = interaction.user.id

        try:
            # upsert（既にあれば更新、なければ追加）
            supabase.table("user_vr").upsert(
                {
                    "user_id": user_id,
                    "vr": vr
                },
                on_conflict="user_id"
            ).execute()

            await interaction.response.send_message(
                f"✅ VRを **{vr}** で登録しました。",
                ephemeral=True
            )

        except Exception as e:
            await interaction.response.send_message(
                "❌ VRの登録に失敗しました。",
                ephemeral=True
            )
            print(f"[vr_register] error: {e}")


# スラッシュコマンド登録
async def setup(bot: commands.Bot):
    await bot.add_cog(Player(bot))
