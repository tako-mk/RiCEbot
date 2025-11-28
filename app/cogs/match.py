import os
import asyncpg
import discord
from discord import app_commands
from discord.ui import View, Button
from discord.ext import commands

DATABASE_URL = os.getenv("DATABASE_URL")  # Supabase URL

class ResultListView(View):
    def __init__(self, embeds):
        super().__init__(timeout=None)
        self.embeds = embeds
        self.index = 0

    async def update_message(self, interaction):
        await interaction.message.edit(embed=self.embeds[self.index], view=self)

    @discord.ui.button(label="前へ", style=discord.ButtonStyle.secondary)
    async def prev(self, button: Button, interaction: discord.Interaction):
        if self.index > 0:
            self.index -= 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="次へ", style=discord.ButtonStyle.secondary)
    async def next(self, button: Button, interaction: discord.Interaction):
        if self.index < len(self.embeds) - 1:
            self.index += 1
            await self.update_message(interaction)
        else:
            await interaction.response.defer()


async def get_conn():
    return await asyncpg.connect(DATABASE_URL)


class Match(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="register_a")
    async def register_a(
        self, interaction: discord.Interaction,
        hour: str,
        mypoint: int,
        enemy1: str, point1: int,
        enemy2: str, point2: int,
        enemy3: str, point3: int,
        date: str
    ):
        """4チーム戦の結果を登録"""
        role = discord.utils.get(interaction.guild.roles, name=f"{hour}h")
        if not role or not role.members:
            await interaction.response.send_message("そのhourにメンバーがいません。", ephemeral=True)
            return

        players_text = ",".join([m.name for m in role.members])
        scores = [mypoint, point1, point2, point3]
        my_rank = sorted(scores, reverse=True).index(mypoint) + 1
        datetime_str = f"{date} {hour}:00"

        conn = await get_conn()
        try:
            await conn.execute("""
                INSERT INTO result_a
                (player, my_point, enemy1, point1, enemy2, point2, enemy3, point3, rank, date)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
            """, players_text, mypoint, enemy1, point1, enemy2, point2, enemy3, point3, my_rank, datetime_str)
        finally:
            await conn.close()

        embed = discord.Embed(title="リザルト登録完了", color=0x1abc9c)
        embed.add_field(name="日時", value=datetime_str)
        embed.add_field(name="メンバー", value=players_text)
        embed.add_field(name="得点", value=mypoint)
        embed.add_field(name="敵1", value=f"{enemy1}: {point1}")
        embed.add_field(name="敵2", value=f"{enemy2}: {point2}")
        embed.add_field(name="敵3", value=f"{enemy3}: {point3}")
        embed.add_field(name="順位", value=f"{my_rank}位")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="register_b")
    async def register_b(
        self, interaction: discord.Interaction,
        hour: str,
        mypoint: int,
        enemy: str,
        enemy_point: int,
        date: str
    ):
        """2チーム戦の結果を登録"""
        role = discord.utils.get(interaction.guild.roles, name=f"{hour}h")
        if not role or not role.members:
            await interaction.response.send_message("そのhourにメンバーがいません。", ephemeral=True)
            return

        players_text = ",".join([m.name for m in role.members])
        scores = [mypoint, enemy_point]
        my_rank = sorted(scores, reverse=True).index(mypoint) + 1
        datetime_str = f"{date} {hour}:00"

        conn = await get_conn()
        try:
            await conn.execute("""
                INSERT INTO result_b
                (player, my_point, enemy, enemy_point, rank, date)
                VALUES ($1,$2,$3,$4,$5,$6)
            """, players_text, mypoint, enemy, enemy_point, my_rank, datetime_str)
        finally:
            await conn.close()

        embed = discord.Embed(title="リザルト登録完了", color=0x1abc9c)
        embed.add_field(name="日時", value=datetime_str)
        embed.add_field(name="メンバー", value=players_text)
        embed.add_field(name="得点", value=mypoint)
        embed.add_field(name="敵", value=f"{enemy}: {enemy_point}")
        embed.add_field(name="順位", value=f"{my_rank}位")
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="result_list")
    async def result_list(
        self, interaction: discord.Interaction,
        type: str,
        enemy: str = None,
    ):
        type = type.lower()
        if type not in ("a", "b"):
            await interaction.response.send_message("typeは a/b で指定してください", ephemeral=True)
            return

        table = "result_a" if type == "a" else "result_b"
        conn = await get_conn()
        try:
            if enemy:
                if type == "a":
                    rows = await conn.fetch(f"""
                        SELECT * FROM {table} WHERE enemy1=$1 OR enemy2=$1 OR enemy3=$1
                    """, enemy)
                else:
                    rows = await conn.fetch(f"SELECT * FROM {table} WHERE enemy=$1", enemy)
            else:
                rows = await conn.fetch(f"SELECT * FROM {table}")
        finally:
            await conn.close()

        if not rows:
            await interaction.response.send_message("該当する結果はありません。", ephemeral=True)
            return

        rank_counts = {}
        for row in rows:
            r = row["rank"]
            rank_counts[r] = rank_counts.get(r, 0) + 1
        total_matches = len(rows)

        embeds = []
        for i in range(0, len(rows), 15):
            embed = discord.Embed(title="結果一覧", color=0x3498db)
            for row in rows[i:i + 15]:
                if type == "a":
                    text = (f"メンバー: {row['player']}\n"
                            f"自チーム: {row['my_point']}pt\n"
                            f"{row['enemy1']}: {row['point1']}pt\n"
                            f"{row['enemy2']}: {row['point2']}pt\n"
                            f"{row['enemy3']}: {row['point3']}pt\n"
                            f"順位: {row['rank']}位")
                else:
                    text = (f"メンバー: {row['player']}\n"
                            f"自チーム: {row['my_point']}pt\n"
                            f"敵: {row['enemy']} {row['enemy_point']}pt\n"
                            f"順位: {row['rank']}位")
                embed.add_field(name=f"ID:{row['result_id']} | 日時: {row['date']}", value=text, inline=False)
            rank_text = "\n".join([f"{k}位: {v}回" for k, v in sorted(rank_counts.items())])
            embed.add_field(name=f"合計試合数: {total_matches}", value=rank_text, inline=False)
            embeds.append(embed)

        view = ResultListView(embeds)
        await interaction.response.send_message(embed=embeds[0], view=view)

async def setup(bot):
    await bot.add_cog(Match(bot))
