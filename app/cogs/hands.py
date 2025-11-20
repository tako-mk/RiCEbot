import discord
from discord.ui import View, Button
import os
import json
import random
from discord import app_commands
from discord.ext import commands

HOUR_JSON = os.path.join(os.path.dirname(__file__), "..", "hours.json")

# 挙手機能用のhours読み込み関数
def load_hours():
    if not os.path.exists(HOUR_JSON):
        return {}  # ファイルがなければ空の dict
    with open(HOUR_JSON, "r", encoding="utf-8") as f:
        try:
            data = json.load(f)
        except json.JSONDecodeError:
            # 空ファイルや破損ファイルの場合も空 dict
            data = {}
    return data

def save_hours(data):
    with open(HOUR_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# Embed生成関数
async def build_embed(guild: discord.Guild):
    hours = load_hours()
    embed = discord.Embed(title="挙手List", color=0x3498db)

    if not hours:
        embed.description = "現在登録されているhourはありません。"
        return embed

    for hour, role_id in hours.items():
        role = guild.get_role(role_id)
        if role is None:
            continue
        
        members = [m.mention for m in role.members]
        text = "なし" if len(members) == 0 else "\n".join(members)
        embed.add_field(name=f"{hour} 時", value=text, inline=False)

    return embed

# Embedの下のボタンの関数
class HourButtonView(View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=None)
        self.guild = guild
        hours = load_hours()

        for hour, role_id in hours.items():
            self.add_item(HourButton(hour, role_id))

class HourButton(Button):
    def __init__(self, hour, role_id):
        super().__init__(label=hour, style=discord.ButtonStyle.primary)
        self.hour = hour
        self.role_id = role_id

    async def callback(self, interaction: discord.Interaction):
        role = interaction.guild.get_role(self.role_id)
        if role is None:
            await interaction.response.send_message("ロールが存在しません。", ephemeral=True)
            return
        
        member = interaction.user

        if role in member.roles:
            await member.remove_roles(role)
            msg = f"{self.hour} 時から **退出** しました。"
        else:
            await member.add_roles(role)
            msg = f"{self.hour} 時に **参加** しました。"

        # Embedを更新
        embed = await build_embed(interaction.guild)
        view = HourButtonView(interaction.guild)

        await interaction.response.edit_message(embed=embed, view=view)

# スラッシュコマンド
class Handraise(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="set")
    async def set_hour(self, interaction: discord.Interaction, hour: str):
        """hourの登録"""
        hours = load_hours()

        # ロール作成
        role = await interaction.guild.create_role(name=f"{hour}h")
        hours[hour] = role.id
        save_hours(hours)

        embed = await build_embed(interaction.guild)
        view = HourButtonView(interaction.guild)

        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="out")
    async def out_hour(self, interaction: discord.Interaction, hour: str):
        """hourの削除"""
        hours = load_hours()
        if hour not in hours:
            await interaction.response.send_message("そのhourはありません。", ephemeral=True)
            return

        role = interaction.guild.get_role(hours[hour])
        if role:
            await role.delete()

        del hours[hour]
        save_hours(hours)

        embed = await build_embed(interaction.guild)
        view = HourButtonView(interaction.guild)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="now")
    async def now(self, interaction: discord.Interaction):
        """現在の挙手状況を確認"""
        embed = await build_embed(interaction.guild)
        view = HourButtonView(interaction.guild)
        await interaction.response.send_message(embed=embed, view=view)

    @app_commands.command(name="can")
    async def can_hour(self, interaction: discord.Interaction, hour: str):
        """交流戦への挙手"""
        hours = load_hours()
        if hour not in hours:
            await interaction.response.send_message("そのhourはありません。", ephemeral=True)
            return
        
        role = interaction.guild.get_role(hours[hour])
        member = interaction.user

        if role in member.roles:
            msg = f"{hour} 時には既に登録されています。"
        else:
            await member.add_roles(role)
            msg = f"{hour} 時に挙手しました。"

        embed = await build_embed(interaction.guild)
        view = HourButtonView(interaction.guild)
        await interaction.response.send_message(msg, embed=embed, view=view)

    @app_commands.command(name="drop")
    async def drop_hour(self, interaction: discord.Interaction, hour: str):
        """挙手の取り消し"""
        hours = load_hours()
        if hour not in hours:
            await interaction.response.send_message("そのhourはありません。", ephemeral=True)
            return
        
        role = interaction.guild.get_role(hours[hour])
        member = interaction.user

        if role in member.roles:
            await member.remove_roles(role)
            msg = f"{hour} 時の挙手を取り消しました。"
        else:
            msg = f"{hour} 時には登録されていません。"

        embed = await build_embed(interaction.guild)
        view = HourButtonView(interaction.guild)
        await interaction.response.send_message(msg, embed=embed, view=view)

    @app_commands.command(name="clear")
    async def clear_hours(self, interaction: discord.Interaction):
        """挙手状況のクリア"""
        hours = load_hours()
        for role_id in hours.values():
            role = interaction.guild.get_role(role_id)
            if role:
                for member in role.members:
                    await member.remove_roles(role)

        embed = await build_embed(interaction.guild)
        view = HourButtonView(interaction.guild)
        await interaction.response.send_message("✅ 全ての挙手状況をクリアしました。", embed=embed, view=view)

    @app_commands.command(name="pick")
    async def pick_hour(self, interaction: discord.Interaction, hour: str):
        """そのhourのメンバーからランダムで1人選ぶ"""
        hours = load_hours()
        if hour not in hours:
            await interaction.response.send_message("そのhourはありません。", ephemeral=True)
            return
        
        role = interaction.guild.get_role(hours[hour])
        if not role or not role.members:
            await interaction.response.send_message("そのhourに登録されているメンバーがいません。", ephemeral=True)
            return

        member = random.choice(role.members)
        await interaction.response.send_message(f" {hour} の外交担当: {member.mention}")

async def setup(bot):
    await bot.add_cog(Handraise(bot))
