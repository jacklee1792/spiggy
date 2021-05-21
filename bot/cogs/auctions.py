from collections import defaultdict
from configparser import ConfigParser
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from discord import File, TextChannel
from discord.ext import tasks
from discord.ext.commands import Bot, Cog
from discord_slash import SlashCommandOptionType, SlashContext
from discord_slash.utils.manage_commands import create_option

from backend.controllers.ahcontrol import AuctionHouseObserver
from backend.database import database
from bot import utils
from bot.utils import cog_slash
from models.auction import ActiveAuction


_here = Path(__file__).parent
_cfg = ConfigParser()
_cfg.read(_here.parent.parent / 'config/spiggy.ini')

CHECK_COOLDOWN = _cfg['AH Caching'].getfloat('CheckCooldown')
PRICE_POINT_SPAN = _cfg['AH Caching'].getfloat('PricePointSpan')


class AuctionsCog(Cog):
    """
    Bot cog which handles auction commands.
    """
    bot: Bot
    obs: AuctionHouseObserver
    lbin_stats: Dict[Tuple[str, str], List[Tuple[float, int]]]
    data_points: int

    def __init__(self, bot: Bot) -> None:
        """
        Initialize the cog.

        :param bot: The bot object which holds this cog.
        """
        self.bot = bot
        self.obs = AuctionHouseObserver()
        self.lbin_stats = defaultdict(list)
        self.data_points = 0

        # Maintain lowest BIN statistics
        self.obs.add_observer(self.update_lbin_statistics)

        # Update name linking table
        self.obs.add_observer(self.update_name_links)

        self.check_new_auctions.start()

    @cog_slash(
        name='lbin',
        description='Get lowest BIN prices on the given item',
        options=[
            create_option(
                name='item',
                description='The name of the item to check',
                option_type=SlashCommandOptionType.STRING,
                required=True
            )
        ]
    )
    async def lbin(self, ctx: SlashContext, item: str) -> None:
        item_id = database.guess_item_id(item)
        if not self.obs.active_auctions:
            await ctx.send('No active auctions cached!')
            return
        else:
            def is_match(auction: ActiveAuction):
                return auction.item.item_id == item_id and auction.is_bin
            matches = [auction for auction in self.obs.active_auctions
                       if is_match(auction)]
            matches.sort(key=lambda a: a.price)
            matches = matches[:5]
            for match in matches:
                await ctx.send(f'{match.seller.username} {match.price}')

    @cog_slash(
        name='endsoon',
        description='Get auctions which are ending soon for a given item',
        options=[
            create_option(
                name='item',
                description='The name of the item to check',
                option_type=SlashCommandOptionType.STRING,
                required=True
            )
        ]
    )
    async def endsoon(self, ctx: SlashContext, item: str) -> None:
        item_id = database.guess_item_id(item)
        if not self.obs.active_auctions:
            await ctx.send('No active auctions cached!')
            return
        else:
            def is_match(auction: ActiveAuction):
                return auction.item.item_id == item_id and not auction.is_bin
            matches = [auction for auction in self.obs.active_auctions
                       if is_match(auction)]
            matches.sort(key=lambda a: a.end_time)
            matches = matches[:5]
            for match in matches:
                dt = match.end_time - datetime.now(tz=timezone.utc)
                await ctx.send(f'{match.seller.username} {match.price} '
                               f'(ending in {dt})')

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
                name='span',
                description='The number of previous days to be plotted',
                option_type=SlashCommandOptionType.INTEGER,
                required=False
            ),
            create_option(
                name='rarity',
                description='The rarity of the item to be plotted',
                option_type=SlashCommandOptionType.STRING,
                choices=utils.RARITY_CHOICES,
                required=False
            )
        ]
    )
    async def plot(self, ctx: SlashContext,
                   item: str, span: Optional[int] = None,
                   rarity: Optional[str] = None) -> None:
        await ctx.defer()
        item_id = database.guess_item_id(item)
        try:
            utils.plot_ah_price(item_id, span, rarity)
        except ValueError:
            await ctx.send('Not enough values for the given item!')
            return
        plot_loc = Path(__file__).parent.parent / 'plot.png'
        await ctx.send(file=File(plot_loc, filename='plot.png'))

    def dump_channel(self) -> Optional[TextChannel]:
        """
        Get the dump channel of the bot object.

        :return: The dump channel of the bot object, if it exists.
        """
        return self.bot.cogs['MetaCog'].dump_channel

    @tasks.loop(seconds=CHECK_COOLDOWN)
    async def check_new_auctions(self) -> None:
        """
        Check for new auctions on the obs object.

        :return: None.
        """
        await self.obs.check_new_auctions()

    async def update_lbin_statistics(self) -> None:
        """
        Update the lowest BIN statistics which map (item_id, rarity) pairs to
        a list of lowest prices observed in persisting auctions. Once enough
        data has been collected, record it to the database.

        :return: None.
        """
        current_prices = defaultdict(list)
        for auction in self.obs.persisting_auctions:
            if auction.is_bin:
                key = auction.item.item_id, auction.item.rarity
                current_prices[key].append(auction.unit_price)
        for key, prices in current_prices.items():
            self.lbin_stats[key].append((min(prices), len(prices)))

        self.data_points += 1

        if self.data_points == PRICE_POINT_SPAN:
            d = {}
            for key, stats in self.lbin_stats.items():
                prices, counts = zip(*stats)
                average_lbin = sum(prices) / len(prices)
                occurrences = sum(counts)
                d[key] = (average_lbin, occurrences)
            database.save_prices(d)

            # Log to dump channel
            if dump_channel := self.dump_channel():
                await dump_channel.send('New data point added!')

            # Reset
            self.data_points = 0
            self.lbin_stats = defaultdict(list)

    async def update_name_links(self) -> None:
        """
        Update the name_links table in the database by passing it a list of
        items.

        :return: None.
        """
        items = [auction.item for auction in self.obs.active_auctions]
        database.save_name_links(items)


def setup(bot: Bot):
    bot.add_cog(AuctionsCog(bot))
