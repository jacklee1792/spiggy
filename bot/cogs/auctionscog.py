from configparser import ConfigParser
from datetime import timedelta
from pathlib import Path
from typing import Optional

from discord import Embed, File
from discord.ext.commands import Bot, Cog
from discord_slash import SlashCommandOptionType, SlashContext
from discord_slash.utils.manage_commands import create_choice, create_option

from backend import constants
from backend.controllers.auctionhouse import AuctionHouse
from backend.database import database
from bot import embeds, utils
from bot.utils import cog_slash


_here = Path(__file__).parent
_cfg = ConfigParser()
_cfg.read(_here.parent.parent / 'config/spiggy.ini')

DEFAULT_PLOT_SPAN = _cfg['Plotting'].getint('DefaultPlotSpan')


class AuctionsCog(Cog):
    """
    Bot cog which handles auction commands.
    """
    bot: Bot
    ah: AuctionHouse

    def __init__(self, bot: Bot, ah: AuctionHouse) -> None:
        """
        Initialize the cog.

        :param bot: The bot object which holds this cog.
        :param ah: The AuctionHouse wrapper to use.
        """
        self.bot = bot
        self.ah = ah

    @cog_slash(
        name='plot',
        description='Plot the price of a given item',
        options=[
            create_option(
                name='item',
                description='The name of the item to check',
                option_type=SlashCommandOptionType.STRING,
                required=True
            ),
            create_option(
                name='rarity',
                description='The rarity of the item to be plotted',
                option_type=SlashCommandOptionType.STRING,
                choices=[create_choice(name=value, value=key) for
                         key, value in constants.RARITIES.items()],
                required=False
            ),
            create_option(
                name='span',
                description='The number of previous days to be plotted',
                option_type=SlashCommandOptionType.INTEGER,
                required=False
            )
        ]
    )
    async def plot(self, ctx: SlashContext,
                   item: str, rarity: Optional[str] = None,
                   span: Optional[int] = DEFAULT_PLOT_SPAN) -> None:
        await ctx.defer()

        item_id, basename = database.guess_identifiers(item)
        if rarity is None:
            rarity = database.guess_rarity(item_id)

        embed = Embed()
        embed.title = f'Historical Lowest BIN for {item}'
        try:
            utils.plot_ah_price(item_id, rarity, timedelta(days=span))
        except ValueError:
            embed.description = "I don't have enough information about that " \
                                "item :frowning:"
            embed.colour = embeds.FAIL_COLOUR
            await ctx.send(embed=embed)
            return

        embed.colour = embeds.OK_COLOUR
        file = File(Path(__file__).parent.parent / 'plot.png')
        embed.set_image(url='attachment://plot.png')
        await ctx.send(file=file, embed=embed)
