from typing import Optional
from discord import TextChannel
from discord.ext import commands
from discord.ext.commands import Bot, Cog
from discord.ext.commands.context import Context


class MetaCog(Cog):
    """
    Bot cog which handles meta commands.
    """
    bot: Bot
    dump_channel: Optional[TextChannel]

    def __init__(self, bot: Bot):
        self.bot = bot
        self.dump_channel = None

    @commands.command()
    async def ping(self, ctx: Context):
        await ctx.send('Pong!')

    @commands.command()
    async def setdump(self, ctx: Context):
        self.dump_channel = ctx.channel
        await ctx.send('OK, dump set to this channel.')

    @commands.command()
    async def pingdump(self, ctx: Context):
        if self.dump_channel is None:
            await ctx.send('No dump channel set!')
        else:
            await self.dump_channel.send('Pong!')


def setup(bot: Bot):
    bot.add_cog(MetaCog(bot))
