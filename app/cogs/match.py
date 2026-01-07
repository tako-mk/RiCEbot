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

    with open(MEMBER_FILE, encoding="utf-8") as f:
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

# メンバー入力解決関数(リザルト表示)
def resolve_single_member(token: str, interaction):
    alias_map, id_map = load_member_data()

    # メンション
    if token.startswith("<@"):
        uid = token.replace("<@", "").replace("!", "").replace(">", "")
        return id_map.get(uid)

    # エイリアス
    return alias_map.get(token)

# 勝敗判定関数
def judge(my, enemy):
    if my > enemy:
        return "Win"
    if my < enemy:
        return "Lose"
    return "Draw"

# 順位判定関数
def calc_rank(my_score, others):
    scores = [my_score] + others
    sorted_scores = sorted(scores, reverse=True)

    my_rank = 1
    for s in sorted_scores:
        if s > my_score:
            my_rank += 1

    return my_rank

# 順位ソート関数
def get_sorted_teams_24(r):
    teams = [
        ("RiCE", r["my_score"]),
        (r["enemy1"], r["score1"]),
        (r["enemy2"], r["score2"]),
        (r["enemy3"], r["score3"]),
    ]

    return sorted(
        teams,
        key=lambda x: x[1],
        reverse=True
    )

# ページング計算関数
def calc_pages(data_len: int, per_page: int = 20):
    total_pages = (data_len - 1) // per_page + 1
    start_page = total_pages - 1
    return total_pages, start_page

# Embed生成関数
def build_embed_12(results, page, total_pages):
    lines = []
    win = draw = lose = 0

    for r in results:
        result = judge(r["my_score"], r["enemy_score"])
        if result == "Win": win += 1
        elif result == "Lose": lose += 1
        else: draw += 1

        line = (
            f'{str(r["result_id"]).rjust(3)} '
            f'{str(r["my_score"]).rjust(3)} - '
            f'{str(r["enemy_score"]).rjust(3)} '
            f'{r["enemy"].ljust(5)} '
            f'{result.ljust(4)} '
            f'{r["date"]}'
        )
        lines.append(line)

    embed = discord.Embed(
        title="6v6 戦績",
        description="```text\n" + "\n".join(lines) + "\n```"
    )

    embed.set_footer(
        text=f"Win {win} / Draw {draw} / Lose {lose}  計 {len(results)}回 | {page+1}/{total_pages}"
    )
    return embed

# 24人用Embed生成関数
def build_embed_24(results, page, total_pages):
    lines = []

    for r in results:
        line1 = (
            f'{str(r["result_id"]).rjust(3)} '
            f'RiCE '
            f'{r["enemy1"].ljust(4)} '
            f'{r["enemy2"].ljust(4)} '
            f'{r["enemy3"].ljust(4)}'
        )

        line2 = (
            f'\t'
            f'{str(r["my_score"]).rjust(3)} '
            f'{str(r["score1"]).rjust(3)} '
            f'{str(r["score2"]).rjust(3)} '
            f'{str(r["score3"]).rjust(3)} '
            f'{str(r["rank"])}位 '
            f'{r["date"]}'
        )

        lines.append(line1)
        lines.append(line2)

    embed = discord.Embed(
        title="24人戦 (6v6v6v6) 戦績",
        description="```text\n" + "\n".join(lines) + "\n```"
    )

    embed.set_footer(
        text=f"{len(results)}件 | {page+1}/{total_pages}"
    )
    return embed

# supabase単一データ取得
def fetch_by_id(table: str, result_id: int):
    return (
        supabase.table(table)
        .select("*")
        .eq("result_id", result_id)
        .execute()
        .data
    )

# Embed生成関数(詳細)
def build_result_12_detail_embed(r):
    result = judge(r["my_score"], r["enemy_score"])

    embed = discord.Embed(
        title=f'{r["date"]} 敵 {r["enemy"]}',
        description=(
            f'**{r["my_score"]} - {r["enemy_score"]} {result}**\n\n'
            f'メンバー : {r["player"]}'
        )
    )

    embed.set_footer(text=f'result_id : {r["result_id"]}')
    return embed

# Embed生成関数(詳細24)
def build_result_24_detail_embed(r):
    # チームとスコアをまとめる
    # 点数で降順ソート（同点は並び順維持）
    teams_sorted = get_sorted_teams_24(r)

    # 表示用テキスト作成
    lines = []
    for i, (name, score) in enumerate(teams_sorted, start=1):
        lines.append(f'{i} {name} {score} 点')

    embed = discord.Embed(
        title=f'{r["date"]} 敵 {r["enemy1"]} {r["enemy2"]} {r["enemy3"]}',
        description="**" + "\n".join(lines) + "**"
    )

    embed.add_field(
        name="",
        value=f'メンバー : {r["player"]}',
        inline=False
    )

    embed.set_footer(text=f'result_id : {r["result_id"]}')
    return embed

# 削除前の確認Embed
def build_delete_confirm_12_embed(r):
    result = judge(r["my_score"], r["enemy_score"])

    embed = discord.Embed(
        title="この戦績を削除しますか？",
        description=(
            f'{r["date"]} 敵 {r["enemy"]}\n'
            f'**{r["my_score"]} - {r["enemy_score"]} {result}**\n\n'
            f'メンバー : {r["player"]}'
        )
    )
    embed.set_footer(text=f'result_id : {r["result_id"]}')
    return embed

# 削除前の確認Embed(24)
def build_delete_confirm_24_embed(r):

    teams_sorted = get_sorted_teams_24(r)

    lines = []
    for i, (name, score) in enumerate(teams_sorted, start=1):
        lines.append(f'{i} {name} {score} 点')

    embed = discord.Embed(
        title="この戦績を削除しますか？",
        description=(
            f'{r["date"]} 敵 {r["enemy1"]} {r["enemy2"]} {r["enemy3"]}\n\n'
            f'**' + "\n".join(lines) + '**\n\n'
            f'メンバー : {r["player"]}'
        )
    )

    embed.set_footer(text=f'result_id : {r["result_id"]}')
    return embed

# ページングビュー
class PagedResultView(discord.ui.View):
    def __init__(self, all_results, start_page, build_embed_func):
        super().__init__(timeout=120)
        self.all = all_results
        self.page = start_page
        self.build_embed = build_embed_func

    def get_page(self):
        start = self.page * 20
        return self.all[start:start+20]

    async def update(self, interaction):
        await interaction.response.edit_message(
            embed=self.build_embed(
                self.get_page(),
                self.page,
                (len(self.all)-1)//20 + 1
            ),
            view=self
        )

    @discord.ui.button(label="◀", style=discord.ButtonStyle.secondary)
    async def prev(self, interaction, button):
        if self.page > 0:
            self.page -= 1
            await self.update(interaction)

    @discord.ui.button(label="▶", style=discord.ButtonStyle.secondary)
    async def next(self, interaction, button):
        if (self.page+1)*20 < len(self.all):
            self.page += 1
            await self.update(interaction)

# 削除時の表示
class DeleteConfirm12View(discord.ui.View):
    def __init__(self, result_id: int):
        super().__init__(timeout=60)
        self.result_id = result_id

    @discord.ui.button(label="削除", style=discord.ButtonStyle.danger)
    async def delete(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        supabase.table("result_12").delete().eq(
            "result_id", self.result_id
        ).execute()

        await interaction.response.edit_message(
            content=f"result_id {self.result_id} を削除しました。",
            embed=None,
            view=None
        )

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content="削除をキャンセルしました。",
            embed=None,
            view=None
        )

# 削除時の表示24
class DeleteConfirm24View(discord.ui.View):
    def __init__(self, result_id: int):
        super().__init__(timeout=60)
        self.result_id = result_id

    @discord.ui.button(label="削除", style=discord.ButtonStyle.danger)
    async def delete(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        supabase.table("result_24").delete().eq(
            "result_id", self.result_id
        ).execute()

        await interaction.response.edit_message(
            content=f"result_id {self.result_id} を削除しました。",
            embed=None,
            view=None
        )

    @discord.ui.button(label="キャンセル", style=discord.ButtonStyle.secondary)
    async def cancel(
        self,
        interaction: discord.Interaction,
        button: discord.ui.Button
    ):
        await interaction.response.edit_message(
            content="削除をキャンセルしました。",
            embed=None,
            view=None
        )

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

    # /result_12 (member:○○) (enemy:○○)
    @app_commands.command(name="result_12")
    async def result_12(
        self,
        interaction: discord.Interaction,
        member: str | None = None,
        enemy: str | None = None
    ):
        await interaction.response.defer()

        data = (
            supabase.table("result_12")
            .select("*")
            .order("result_id")
            .execute()
            .data
        )

        # フィルタ
        if member:
            name = resolve_single_member(member, interaction)
            if not name:
                await interaction.followup.send("メンバーが見つかりません")
                return
            data = [r for r in data if name in r["player"].split()]

        if enemy:
            data = [r for r in data if r["enemy"] == enemy]

        if not data:
            await interaction.followup.send("該当する戦績がありません")
            return

        total_pages, start_page = calc_pages(len(data))

        view = PagedResultView(data, start_page, build_embed_12)
        embed = build_embed_12(view.get_page(), start_page, total_pages)

        await interaction.followup.send(embed=embed, view=view)

    # result_12_detail id:○○
    @app_commands.command(
        name="result_12_detail",
        description="6v6戦績の詳細を表示します"
    )
    async def result_12_detail(
        self,
        interaction: discord.Interaction,
        id: int
    ):
        await interaction.response.defer()

        res = fetch_by_id("result_12", id)

        if not res:
            await interaction.followup.send(
                "指定された result_id は存在しません。",
                ephemeral=True
            )
            return

        embed = build_result_12_detail_embed(res[0])
        await interaction.followup.send(embed=embed)

    # result_12_delete
    @app_commands.command(
        name="result_12_delete",
        description="6v6戦績を削除します"
    )
    async def result_12_delete(
        self,
        interaction: discord.Interaction,
        id: int
    ):
        await interaction.response.defer(ephemeral=True)

        res = fetch_by_id("result_12", id)

        if not res:
            await interaction.followup.send(
                "指定された result_id は存在しません。",
                ephemeral=True
            )
            return

        embed = build_delete_confirm_12_embed(res[0])
        view = DeleteConfirm12View(id)

        await interaction.followup.send(
            embed=embed,
            view=view,
            ephemeral=True
        )

    # /register_24 
    @app_commands.command(
        name="register_24",
        description="24人戦(6v6v6v6)の戦績を登録します"
    )
    async def register_24(
        self,
        interaction: discord.Interaction,
        enemy: str,
        scores: str,
        date: str,
        member: str
    ):
        await interaction.response.defer(ephemeral=True)

        try:
            # enemy
            enemies = enemy.split()
            if len(enemies) != 3:
                raise ValueError("enemy は3チーム指定してください")

            # scores
            score_vals = list(map(int, scores.split()))
            if len(score_vals) != 4:
                raise ValueError("scores は4つ指定してください")

            my_score = score_vals[0]
            enemy_scores = score_vals[1:]

            # date
            formatted_date = format_date(date)

            # members
            members = await resolve_members(interaction, member)
            player_str = " ".join(members)

            # rank 計算
            rank = calc_rank(my_score, enemy_scores)

            # insert
            supabase.table("result_24").insert({
                "player": player_str,
                "my_score": my_score,
                "enemy1": enemies[0],
                "score1": enemy_scores[0],
                "enemy2": enemies[1],
                "score2": enemy_scores[1],
                "enemy3": enemies[2],
                "score3": enemy_scores[2],
                "rank": rank,
                "date": formatted_date
            }).execute()

        except Exception as e:
            await interaction.followup.send(
                f"登録失敗: {e}",
                ephemeral=True
            )
            return

        await interaction.followup.send(
            f"24人戦の戦績を登録しました（{rank}位）",
            ephemeral=True
        )

    # /result_24 (member:○○ enemy:○○)
    @app_commands.command(name="result_24")
    async def result_24(
        self,
        interaction: discord.Interaction,
        member: str | None = None,
        enemy: str | None = None
    ):
        await interaction.response.defer()

        data = (
            supabase.table("result_24")
            .select("*")
            .order("result_id")
            .execute()
            .data
        )

        # member フィルタ
        if member:
            name = resolve_single_member(member, interaction)
            if not name:
                await interaction.followup.send("メンバーが見つかりません")
                return
            data = [r for r in data if name in r["player"].split()]

        # enemy フィルタ（3チームのどれかに一致）
        if enemy:
            data = [
                r for r in data
                if enemy in (r["enemy1"], r["enemy2"], r["enemy3"])
            ]

        if not data:
            await interaction.followup.send("該当する戦績がありません")
            return

        total_pages, start_page = calc_pages(len(data))

        view = PagedResultView(data, start_page, build_embed_24)
        embed = build_embed_24(view.get_page(), start_page, total_pages)

        await interaction.followup.send(embed=embed, view=view)

    # /result_24_detail id:○○
    @app_commands.command(
        name="result_24_detail",
        description="24人戦の戦績詳細を表示します"
    )
    async def result_24_detail(
        self,
        interaction: discord.Interaction,
        id: int
    ):
        await interaction.response.defer()

        res = fetch_by_id("result_24", id)

        if not res:
            await interaction.followup.send(
                "指定された result_id は存在しません。",
                ephemeral=True
            )
            return

        embed = build_result_24_detail_embed(res[0])
        await interaction.followup.send(embed=embed)

    # /result_24_delete id:○○
    @app_commands.command(
        name="result_24_delete",
        description="24人戦の戦績を削除します"
    )
    async def result_24_delete(
        self,
        interaction: discord.Interaction,
        id: int
    ):
        await interaction.response.defer(ephemeral=True)

        res = fetch_by_id("result_24", id)

        if not res:
            await interaction.followup.send(
                "指定された result_id は存在しません。",
                ephemeral=True
            )
            return

        embed = build_delete_confirm_24_embed(res[0])
        view = DeleteConfirm24View(id)

        await interaction.followup.send(
            embed=embed,
            view=view,
            ephemeral=True
        )



# スラッシュコマンド登録
async def setup(bot):
    await bot.add_cog(ResultRegister(bot))
