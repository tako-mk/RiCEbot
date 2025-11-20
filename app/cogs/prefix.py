from discord.ext import commands

class PrefixCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="hello")
    async def hello_command(self, ctx):
        await ctx.send("こんにちは！")

    @commands.command(name="kulotan")
    async def kulotan_command(self, ctx):
        await ctx.send("こんにちは！くろたんさん")

    @commands.command(name="Y〇star")
    async def yostar_command(self, ctx):
        await ctx.send("# 爆撃！")


async def setup(bot):
    await bot.add_cog(PrefixCommands(bot))
