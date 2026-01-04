import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import statistics

from services.lounge_api import fetch_mmr


class AveMMR(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(
        name="avemmr",
        description="指定ロールのMMR一覧と平均を表示"
    )
    @app_commands.describe(role="対象のロール")
    async def avemmr(
        self,
        interaction: discord.Interaction,
        role: discord.Role
    ):
        await interaction.response.defer()

        members = [m for m in role.members if not m.bot]

        if not members:
            await interaction.followup.send("そのロールにメンバーがいません。")
            return

        # ---- API並列取得 ----
        tasks = [fetch_mmr(m.id) for m in members]
        results = await asyncio.gather(*tasks)

        mmr_list = []
        lines = []
        skipped = 0

        for member, mmr in zip(members, results):
            if mmr is None:
                skipped += 1
                continue
            mmr_list.append(mmr)
            lines.append(f"{member.display_name}: **{mmr}**")

        if not mmr_list:
            await interaction.followup.send(
                "MMRを取得できるメンバーがいません。"
            )
            return

        avg_mmr = int(statistics.mean(mmr_list))

        # ---- Embed ----
        embed = discord.Embed(
            title=f"{role.name} のMMR",
            description="\n".join(lines[:20]),  # とりあえず20人まで
            color=discord.Color.blue()
        )

        embed.add_field(
            name="平均MMR",
            value=f"**{avg_mmr}**",
            inline=False
        )

        embed.set_footer(
            text=f"{len(mmr_list)}人分 | 未取得 {skipped}人"
        )

        await interaction.followup.send(embed=embed)


async def setup(bot: commands.Bot):
    await bot.add_cog(AveMMR(bot))
