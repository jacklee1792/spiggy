from configparser import ConfigParser
from datetime import timedelta
from pathlib import Path
from typing import List, Optional, Tuple

from discord import Embed, File, Message
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

    :ivar bot: The bot instance which holds this cog.
    :ivar ah: The AuctionHouse instance to use.
    :ivar dashboards: List of tuples representing the dashboards that need to be
    refreshed occasionally.
    """
    bot: Bot
    ah: AuctionHouse
    dashboards: List[Tuple[Message, List, str, str]]

    def __init__(self, bot: Bot, ah: AuctionHouse) -> None:
        """
        Initialize the cog.

        :param bot: The bot object which holds this cog.
        :param ah: The AuctionHouse wrapper to use.
        """
        self.bot = bot
        self.ah = ah
        self.dashboards = []

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
                         key, value in constants.DISPLAY_RARITIES.items()],
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

    @cog_slash(
        subcommand=True,
        checks=[utils.is_owner],
        base='dashboard',
        name='create',
        description='Create a new dashboard',
        options=[
            create_option(
                name='raw',
                description='The Python list to be parsed into a list of items',
                option_type=SlashCommandOptionType.STRING,
                required=True
            ),
            create_option(
                name='title',
                description='The title of the dashboard to be created',
                option_type=SlashCommandOptionType.STRING,
                required=False
            ),
            create_option(
                name='description',
                description='The description of the dashboard to be created',
                option_type=SlashCommandOptionType.STRING,
                required=False
            )
        ]
    )
    async def dashboard_create(self, ctx: SlashContext, raw: str,
                               title: str = 'No title set',
                               description: str = 'No description set') -> None:
        # This is why we need the owner check
        items = eval(raw)
        embed = embeds.dashboard_embed(items=items, title=title,
                                       description=description)
        await ctx.send(embed=embed)
        self.dashboards.append((ctx.message, items, title, description))

    async def refresh_dashboards(self, _) -> None:
        """
        Refresh all of the dashboards.

        :return: None.
        """
        for message, items, title, description in self.dashboards:
            embed = embeds.dashboard_embed(items=items, title=title,
                                           description=description)
            await message.edit(embed=embed)
