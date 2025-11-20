import os
import discord
from discord.ext import commands

# -----------------------
# Bot クラス定義
# -----------------------
class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all(),
        )

    async def setup_hook(self):
        # -----------------------
        # Cog のロード
        # -----------------------
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                await self.load_extension(f"cogs.{filename[:-3]}")

        # -----------------------
        # 永続ビューの再登録
        # -----------------------
        try:
            from cogs.hands import HourButtonView, load_hours
        except ImportError:
            print("⚠️ hands Cog が見つかりません")
            return

        for guild in self.guilds:
            view = HourButtonView(guild)
            self.add_view(view)
        print("✅ Persistent views loaded")


# -----------------------
# Bot インスタンス作成
# -----------------------
bot = MyBot()


# -----------------------
# ログイン完了イベント
# -----------------------
@bot.event
async def on_ready():
    print(f"✅ ログイン成功: {bot.user}")
    # slash コマンドを Discord に同期
    await bot.tree.sync()
    print("✅ スラッシュコマンド同期完了")


# -----------------------
# 実行
# -----------------------
bot.run("DISCORD_BOT_TOKEN")
