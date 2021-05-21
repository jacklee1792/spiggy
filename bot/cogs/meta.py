from typing import Optional

from discord import TextChannel
from discord.ext.commands import Bot, Cog
from discord_slash import SlashContext

from bot import utils
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

    @cog_slash(
        subcommand=True,
        base='dump',
        name='attach',
        description='Set the dump channel',
        checks=[
            utils.check_admin_role
        ])
    async def dump_attach(self, ctx: SlashContext):
        self.dump_channel = ctx.channel
        await ctx.send('OK, dump set to this channel.')

    @cog_slash(
        subcommand=True,
        base='dump',
        name='detach',
        description='Detach from the dump channel',
        checks=[
            utils.check_admin_role
        ])
    async def dump_detach(self, ctx: SlashContext):
        self.dump_channel = None
        await ctx.send('Done!')


def setup(bot: Bot):
    bot.add_cog(MetaCog(bot))
