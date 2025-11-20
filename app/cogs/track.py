import discord
from discord import app_commands
from discord.ext import commands
import os
import json
import jaconv

TRACK_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "track.json")

class Track(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.track_dict = {}
        self.load_tracks()

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


async def setup(bot):
    await bot.add_cog(Track(bot))
