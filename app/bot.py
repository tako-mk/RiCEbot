import os
import discord
from discord.ext import commands
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from cogs.hands import sync_hours_from_roles

class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"OK")

def run_server():
    server = HTTPServer(("0.0.0.0", 8000), Handler)
    server.serve_forever()


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
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py") and filename != "__init__.py":
                await self.load_extension(f"cogs.{filename[:-3]}")

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
    await bot.tree.sync()
    print("✅ スラッシュコマンド同期完了")
    for guild in bot.guilds:
        await sync_hours_from_roles(guild)


# -----------------------
# 実行
# -----------------------
# Discord Bot を起動する前にスレッドで HTTP サーバーを起動
threading.Thread(target=run_server, daemon=True).start()
TOKEN = os.environ.get("DISCORD_BOT_TOKEN")
if not TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN が環境変数に設定されていません")
bot.run(TOKEN)
