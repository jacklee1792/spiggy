from typing import Optional

from discord import TextChannel
from discord.ext.commands import Bot, Cog
from discord_slash import SlashContext

from bot.utils import cog_slash


class MetaCog(Cog):
    """
    Bot cog which handles meta commands.
    """
    bot: Bot
    dump_channel: Optional[TextChannel]

    def __init__(self, bot: Bot):
        self.bot = bot
        self.dump_channel = None

    @cog_slash(
        name='ping',
        description='Ping the bot'
    )
    async def ping(self, ctx: SlashContext):
        await ctx.send('Pong!')
