import sqlite3
import os
import math
import discord
from discord import app_commands
from discord.ui import View, Button
from discord.ext import commands

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "db", "result.db")


def get_conn():
    return sqlite3.connect(DB_PATH)

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
        if not role:
            await interaction.response.send_message("そのhourは存在しません。", ephemeral=True)
            return

        members = role.members
        if not members:
            await interaction.response.send_message("ロールにメンバーがいません。", ephemeral=True)
            return

        # メンバーを文字列化
        players_text = ",".join([m.name for m in members])

        # 順位計算
        scores = [mypoint, point1, point2, point3]
        sorted_scores = sorted(scores, reverse=True)
        my_rank = sorted_scores.index(mypoint) + 1

        conn = get_conn()
        cursor = conn.cursor()

        # 1試合1レコードに変更
        cursor.execute("""
        INSERT INTO result_a
        (player, my_point, enemy1, point1, enemy2, point2, enemy3, point3, rank, date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            players_text, mypoint, enemy1, point1, enemy2, point2, enemy3, point3,
            my_rank, f"{date}{hour}"
        ))

        conn.commit()
        conn.close()

        # Embed（1つだけ）
        embed = discord.Embed(title="リザルト登録完了", color=0x1abc9c)
        embed.add_field(name="日時", value=f"{date} {hour}時")
        embed.add_field(name="メンバー", value=players_text)
        embed.add_field(name="得点", value=mypoint)
        embed.add_field(name="敵1", value=f"{enemy1}: {point1}")
        embed.add_field(name="敵2", value=f"{enemy2}: {point2}")
        embed.add_field(name="敵3", value=f"{enemy3}: {point3}")
        embed.add_field(name="順位", value=f"{my_rank}位")

        await interaction.response.send_message(embed=embed)


    # /register_b コマンド（2チーム戦）
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
        if not role:
            await interaction.response.send_message("そのhourは存在しません。", ephemeral=True)
            return

        members = role.members
        if not members:
            await interaction.response.send_message("ロールにメンバーがいません。", ephemeral=True)
            return

        # メンバーまとめ
        players_text = ",".join([m.name for m in members])

        # 順位算出
        scores = [mypoint, enemy_point]
        my_rank = sorted(scores, reverse=True).index(mypoint) + 1

        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO result_b
        (player, my_point, enemy, enemy_point, rank, date)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            players_text, mypoint, enemy, enemy_point,
            my_rank, f"{date}{hour}"
        ))

        conn.commit()
        conn.close()

        embed = discord.Embed(title="リザルト登録完了", color=0x1abc9c)
        embed.add_field(name="日時", value=f"{date} {hour}時")
        embed.add_field(name="メンバー", value=players_text)
        embed.add_field(name="得点", value=mypoint)
        embed.add_field(name="敵", value=f"{enemy}: {enemy_point}")
        embed.add_field(name="順位", value=f"{my_rank}位")

        await interaction.response.send_message(embed=embed)

    # /result_list コマンド
    @app_commands.command(name="result_list")
    async def result_list(
        self, interaction: discord.Interaction,
        type: str,
        enemy: str = None,
    ):
        """結果一覧を表示（type: a/b）"""
        type = type.lower()
        if type not in ("a", "b"):
            await interaction.response.send_message("typeは a または b で指定してください。", ephemeral=True)
            return

        table = "result_a" if type == "a" else "result_b"

        conn = get_conn()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        if enemy:
            # a の時は敵1/2/3 にヒット
            if type == "a":
                cursor.execute(f"""
                    SELECT * FROM {table}
                    WHERE enemy1=? OR enemy2=? OR enemy3=?
                """, (enemy, enemy, enemy))
            else:
                cursor.execute(f"""
                    SELECT * FROM {table}
                    WHERE enemy=?
                """, (enemy,))
        else:
            cursor.execute(f"SELECT * FROM {table}")

        rows = cursor.fetchall()
        conn.close()

        if not rows:
            await interaction.response.send_message("該当する結果はありません。", ephemeral=True)
            return

        # 順位集計
        rank_counts = {}
        for row in rows:
            r = row["rank"]
            rank_counts[r] = rank_counts.get(r, 0) + 1
        total_matches = len(rows)

        # Embedページング（15件ずつ）
        embeds = []
        for i in range(0, len(rows), 15):
            embed = discord.Embed(title="結果一覧", color=0x3498db)

            for row in rows[i:i+15]:
                rid = row["result_id"]
                date = row["date"]
                players = row["players"]
                rank = row["rank"]

                if type == "a":
                    text = (
                        f"メンバー: {players}\n"
                        f"自チーム: {row['my_point']}pt\n"
                        f"{row['enemy1']}: {row['point1']}pt\n"
                        f"{row['enemy2']}: {row['point2']}pt\n"
                        f"{row['enemy3']}: {row['point3']}pt\n"
                        f"順位: {rank}位"
                    )
                else:
                    text = (
                        f"メンバー: {players}\n"
                        f"自チーム: {row['my_point']}pt\n"
                        f"{row['enemy']}: {row['enemy_point']}pt\n"
                        f"順位: {rank}位"
                    )

                embed.add_field(
                    name=f"ID:{rid} | 日時: {date}",
                    value=text,
                    inline=False
                )

            rank_text = "\n".join([f"{k}位: {v}回" for k, v in sorted(rank_counts.items())])
            embed.add_field(name=f"合計試合数: {total_matches}", value=rank_text, inline=False)
            embeds.append(embed)

        view = ResultListView(embeds)
        await interaction.response.send_message(embed=embeds[0], view=view)

    # /result_edit コマンド
    @app_commands.command(name="result_edit")
    async def result_edit(
        self, interaction: discord.Interaction,
        type: str,
        result_id: int,
        target: str,
        set: str
    ):
        """指定result_idの内容を書き換え"""
        type = type.lower()
        if type not in ("a", "b"):
            await interaction.response.send_message("typeは a または b で指定してください。", ephemeral=True)
            return

        table = "result_a" if type == "a" else "result_b"

        conn = get_conn()
        cursor = conn.cursor()

        cursor.execute(f"PRAGMA table_info({table})")
        columns = [c[1] for c in cursor.fetchall()]

        if target not in columns:
            conn.close()
            await interaction.response.send_message(f"{target} は存在しません。", ephemeral=True)
            return

        cursor.execute(f"UPDATE {table} SET {target}=? WHERE result_id=?", (set, result_id))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"✅ {result_id} の {target} を {set} に更新しました。")

    # /result_delete コマンド
    @app_commands.command(name="result_delete")
    async def result_delete(
        self, interaction: discord.Interaction,
        type: str,
        result_id: int
    ):
        """指定result_idの削除"""
        type = type.lower()
        if type not in ("a", "b"):
            await interaction.response.send_message("typeは a または b で指定してください。", ephemeral=True)
            return

        conn = get_conn()
        cursor = conn.cursor()
        table = "result_a" if type == "a" else "result_b"
        cursor.execute(f"DELETE FROM {table} WHERE result_id=?", (result_id,))
        conn.commit()
        conn.close()
        await interaction.response.send_message(f"✅ {result_id} を削除しました。")


async def setup(bot):
    await bot.add_cog(Match(bot))

