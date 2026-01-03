import discord
from discord.ui import View, Button
import os
import json
import random
from discord import app_commands
from discord.ext import commands
import re

HOUR_JSON = os.path.join(os.path.dirname(__file__), "..", "hours.json")
MSG_JSON = os.path.join(os.path.dirname(__file__), "..", "handraise_message.json")

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

# 挙手機能用のhours書込み関数
def save_hours(data):
    with open(HOUR_JSON, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# botダウン時のhours再構築
async def sync_hours_from_roles(guild: discord.Guild):
    """
    サーバー内の ○○h ロールを走査して hours.json を再構築する
    """
    temp = {}

    for role in guild.roles:
        m = re.fullmatch(r"(\d+)h", role.name)
        if m:
            hour = int(m.group(1))   # 数値にする
            temp[hour] = role.id

    # hour昇順でソートしてdictに戻す
    hours = {str(hour): role_id for hour, role_id in sorted(temp.items())}

    save_hours(hours)

def load_message_id():
    if not os.path.exists(MSG_JSON):
        return None
    with open(MSG_JSON, "r", encoding="utf-8") as f:
        try:
            return json.load(f).get("message_id")
        except json.JSONDecodeError:
            return None

def save_message_id(message_id: int):
    with open(MSG_JSON, "w", encoding="utf-8") as f:
        json.dump({"message_id": message_id}, f, indent=2)


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
        
        members = [f"・{m.display_name}" for m in role.members]
        text = "なし" if len(members) == 0 else "\n".join(members)
        embed.add_field(name=f"{hour} 時", value=text, inline=False)

    return embed

# Embed更新関数
async def resend_handraise_embed(channel: discord.TextChannel, guild: discord.Guild):
    # 旧メッセージ削除
    old_id = load_message_id()
    if old_id:
        try:
            msg = await channel.fetch_message(old_id)
            await msg.delete()
        except discord.NotFound:
            pass

    # 新しく送信
    embed = await build_embed(guild)
    view = HourButtonView(guild)
    new_msg = await channel.send(embed=embed, view=view)

    save_message_id(new_msg.id)

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
        else:
            await member.add_roles(role)

        # Embedを再送で更新
        await resend_handraise_embed(interaction.channel, interaction.guild)

        # interaction未応答防止（表示しないACK）
        await interaction.response.defer(ephemeral=True)

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
        await resend_handraise_embed(interaction.channel, interaction.guild)
        await interaction.response.send_message("現在の挙手状況を更新しました。", ephemeral=True)

    @app_commands.command(name="can")
    async def can_hour(
        self,
        interaction: discord.Interaction,
        hour: str,
        name: discord.Member | None = None
    ):
        """交流戦への挙手（自分 or 指定ユーザー）"""
        hours = load_hours()
        if hour not in hours:
            await interaction.response.send_message("そのhourはありません。", ephemeral=True)
            return
        
        role = interaction.guild.get_role(hours[hour])
        target = name or interaction.user
    
        if role in target.roles:
            msg = f"{target.mention} は {hour} 時に既に登録されています。"
        else:
            await target.add_roles(role)
            msg = f"{target.mention} を {hour} 時に挙手させました。"
    
        # 最後の挙手Embedを更新
        await resend_handraise_embed(interaction.channel, interaction.guild)
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="drop")
    async def drop_hour(
        self,
        interaction: discord.Interaction,
        hour: str,
        name: discord.Member | None = None
    ):
        """交流戦の挙手取り下げ（自分 or 指定ユーザー）"""
        hours = load_hours()
        if hour not in hours:
            await interaction.response.send_message("そのhourはありません。", ephemeral=True)
            return
        
        role = interaction.guild.get_role(hours[hour])
        target = name or interaction.user
    
        if role not in target.roles:
            msg = f"{target.mention} は {hour} 時に登録されていません。"
        else:
            await target.remove_roles(role)
            msg = f"{target.mention} の {hour} 時の挙手を取り下げました。"
    
        # 最後の挙手Embedを更新
        await resend_handraise_embed(interaction.channel, interaction.guild)
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="clear")
    async def clear_hours(self, interaction: discord.Interaction):
        """挙手状況のクリア"""
        hours = load_hours()
        for role_id in hours.values():
            role = interaction.guild.get_role(role_id)
            if role:
                for member in role.members:
                    await member.remove_roles(role)
    
        # 新しいEmbedを作り直す
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


