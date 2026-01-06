from discord import app_commands
from discord.ext import commands
import discord
from services.supabase import supabase
import os

# メンバーファイルの場所
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MEMBER_FILE = os.path.normpath(
    os.path.join(BASE_DIR, "..", "data", "member.txt")
)

# 日付変換関数
def format_date(date_str: str) -> str:
    # yyyymmddhh
    return f"{date_str[0:4]}/{date_str[4:6]}/{date_str[6:8]} {date_str[8:10]}"

# メンバー変換関数
def load_member_data():
    alias_map = {}      # alias -> 登録名
    id_map = {}         # discord_id -> 登録名

    with MEMBER_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            name, discord_id, aliases = line.split(":")
            id_map[discord_id] = name

            for a in aliases.split(","):
                alias_map[a] = name

    return alias_map, id_map

# メンバー入力解決関数
async def resolve_members(
    interaction: discord.Interaction,
    member_arg: str
) -> list[str]:
    alias_map, id_map = load_member_data()
    result = []

    # ロール指定 (@22h など)
    if member_arg.startswith("<@&"):
        role_id = int(member_arg.replace("<@&", "").replace(">", ""))
        role = interaction.guild.get_role(role_id)
        if role is None:
            raise ValueError("指定されたロールが存在しません")

        for m in role.members:
            if m.bot:
                continue
            if str(m.id) in id_map:
                result.append(id_map[str(m.id)])

    else:
        # 名前列挙
        for token in member_arg.split():
            if token not in alias_map:
                raise ValueError(f"未登録メンバー: {token}")
            result.append(alias_map[token])

    if len(result) != 6:
        raise ValueError("メンバーは6人である必要があります")

    return result

# リザルト関連のコマンド
class ResultRegister(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    # /register_12
    @app_commands.command(
        name="register_12",
        description="6v6戦績を登録します"
    )
    async def register_12(
        self,
        interaction: discord.Interaction,
        enemy: str,
        scores: str,
        date: str,
        member: str
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            # scores
            my_score, enemy_score = map(int, scores.split())

            # date
            formatted_date = format_date(date)

            # members
            members = await resolve_members(interaction, member)
            player_str = " ".join(members)

            # insert
            supabase.table("result_12").insert({
                "player": player_str,
                "my_score": my_score,
                "enemy": enemy,
                "enemy_score": enemy_score,
                "date": formatted_date
            }).execute()

        except Exception as e:
            await interaction.followup.send(
                f"登録失敗: {e}",
                ephemeral=True
            )
            return

        await interaction.followup.send(
            "戦績を登録しました。",
            ephemeral=True
        )
