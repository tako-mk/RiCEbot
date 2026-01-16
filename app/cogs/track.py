import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import jaconv

TRACK_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "track.json")
CONNECT_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "track_connect.json")
NUMBER_EMOJIS = ["0️⃣", "1️⃣", "2️⃣", "3️⃣", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]

class ConnectView(discord.ui.View):
    def __init__(self, connects, end_name):
        super().__init__(timeout=180)
        self.connects = connects
        self.end_name = end_name

        for i, _ in enumerate(connects):
            self.add_item(ConnectButton(i))

class ConnectButton(discord.ui.Button):
    def __init__(self, index: int):
        super().__init__(
            style=discord.ButtonStyle.primary,
            emoji=f"{index}\N{COMBINING ENCLOSING KEYCAP}"
        )
        self.index = index

    async def callback(self, interaction: discord.Interaction):
        view: ConnectView = self.view
        data = view.connects[self.index]

        start = data["start"]
        end = data["end"]
        desc = data["description"]
        movie = data.get("movie", "未登録")

        embed = discord.Embed(
            title=f"{start} → {end}",
            description=desc,
            color=0x1abc9c
        )

        content = None

        if movie == "未登録":
            embed.add_field(
                name="動画",
                value="動画が未登録です。",
                inline=False
            )
        else:
            # Embed外にリンクを出す
            content = movie

        await interaction.response.edit_message(
            content=content,
            embed=embed,
            view=None
        )


class Track(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.track_dict = {}
        self.load_tracks()
        self.connects = []
        self.load_connects()


    def normalize(self, s: str) -> str:
        """入力文字列を小文字・カタカナ統一・全角半角吸収"""
        s = s.strip().lower()            # 前後スペース除去＆小文字化
        s = jaconv.hira2kata(s)          # ひらがな → カタカナ
        s = jaconv.z2h(s, kana=False, digit=True, ascii=True)  # 全角数字・英字 → 半角
        return s

    def load_tracks(self):
        """track.json を読み込み、alias -> (name, image_url) の辞書にする"""
        self.track_dict = {}
        if not os.path.exists(TRACK_FILE):
            print(f"track.json が見つかりません: {TRACK_FILE}")
            return
        
        with open(TRACK_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError as e:
                print(f"JSON 読み込みエラー: {e}")
                return

        for entry in data:
            name = entry.get("name")
            image_url = entry.get("image")
            aliases = entry.get("aliases", [])
            for alias in aliases:
                normalized_alias = self.normalize(alias)
                self.track_dict[normalized_alias] = (name, image_url)
                print(f"登録: {normalized_alias} -> {name}")  # 確認用

    def load_connects(self):
        self.connects = []
        if not os.path.exists(CONNECT_FILE):
            print("track_connect.json が見つかりません")
            return

        with open(CONNECT_FILE, "r", encoding="utf-8") as f:
            try:
                self.connects = json.load(f)
            except json.JSONDecodeError as e:
                print(f"connect JSON エラー: {e}")

    # /track name:○○
    @app_commands.command(name="track")
    async def track(self, interaction: discord.Interaction, name: str):
        """指定コースの情報を表示"""
        normalized_name = self.normalize(name)
        if normalized_name not in self.track_dict:
            await interaction.response.send_message(
                f"コース「{name}」は見つかりませんでした。", ephemeral=True
            )
            return

        track_name, image_url = self.track_dict[normalized_name]
        embed = discord.Embed(title=track_name, color=0x1abc9c)
        embed.set_image(url=image_url)
        await interaction.response.send_message(embed=embed)

    # /ctrack name:○○
    @app_commands.command(name="ctrack")
    async def ctrack(self, interaction: discord.Interaction, name: str):
        normalized = self.normalize(name)

        if normalized not in self.track_dict:
            await interaction.response.send_message(
                f"コース「{name}」は見つかりませんでした。",
                ephemeral=True
            )
            return

        end_name, _ = self.track_dict[normalized]

        # 終点が一致する接続を集める
        matched = [
            c for c in self.connects
            if self.normalize(c["end"]) == self.normalize(end_name)
        ]

        if not matched:
            await interaction.response.send_message(
                f"「{end_name}」を終点とする接続は見つかりません。",
                ephemeral=True
            )
            return

        lines = []
        for i, c in enumerate(matched):
            lines.append(f"{i}️⃣ {c['start']}")

        embed = discord.Embed(
            title=f'終点「{end_name}」',
            description="\n".join(lines),
            color=0x1abc9c
        )

        view = ConnectView(matched, end_name)
        await interaction.response.send_message(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(Track(bot))
