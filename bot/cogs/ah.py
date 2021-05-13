from discord import TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Cog
from discord.ext.commands.context import Context
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict
from collections import defaultdict

from backend.controllers.ahcontrol import AuctionHouseObserver
from models.auction import ActiveAuction
from backend.database import database


class AuctionHouseCog(Cog):
    """
    Bot cog which handles auction commands.
    """
    bot: Bot
    obs: AuctionHouseObserver
    lbin_stats: Dict[Tuple[str, str], List[float]]
    update_lbin_calls: int

    def __init__(self, bot: Bot) -> None:
        """
        Initialize the cog.

        :param bot: The bot object which holds this cog.
        """
        self.bot = bot
        self.obs = AuctionHouseObserver()
        self.lbin_stats = defaultdict(list)
        self.update_lbin_calls = 0

        # Some sketchy logging for now
        self.obs.add_observer(self.report_obs)
        # Maintain lowest BIN statistics
        self.obs.add_observer(self.update_lbin_statistics)

        self.check_new_auctions.start()

    @commands.command()
    async def lbin(self, ctx: Context, item_id: str):
        if not self.obs.active_auctions:
            return await ctx.send('No active auctions cached!')
        else:
            def is_match(auction: ActiveAuction):
                return auction.item.item_id == item_id and auction.is_bin
            matches = [auction for auction in self.obs.active_auctions
                       if is_match(auction)]
            matches.sort(key=lambda a: a.price)
            matches = matches[:5]
            for match in matches:
                await ctx.send(f'{match.seller.username} {match.price}')

    @commands.command()
    async def endsoon(self, ctx: Context, item_id: str):
        if not self.obs.active_auctions:
            return await ctx.send('No active auctions cached!')
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

    @property
    def dump_channel(self) -> Optional[TextChannel]:
        """
        Get the dump channel of the bot object.

        :return: The dump channel of the bot object, if it exists.
        """
        return self.bot.cogs['MetaCog'].dump_channel

    @tasks.loop(seconds=2)
    async def check_new_auctions(self) -> None:
        """
        Check for new auctions on the obs object.

        :return: None.
        """
        await self.obs.check_new_auctions()

    async def report_obs(self) -> None:
        """
        Report some statistics related to the auction house observer.

        :return: None.
        """
        if self.dump_channel:
            la = len(self.obs.active_auctions)
            le = len(self.obs.ended_auctions)
            lp = len(self.obs.persisting_auctions)
            upd = self.obs.last_update.strftime('%-I:%M:%S %p')
            await self.dump_channel.send(f'Currently, there are {la} active,'
                                         f' {le} ended, and {lp} persisting'
                                         f' auctions in the observer. (Last'
                                         f' updated {upd})')

    async def update_lbin_statistics(self) -> None:
        """
        Update the lowest BIN statistics which map a (item_id, rarity) pair to
        a list of lowest prices observed in persisting auctions. Once enough
        data has been collected, record it to the database.

        :return: None.
        """
        current_prices = defaultdict(list)
        for auction in self.obs.persisting_auctions:
            key = auction.item.item_id, auction.item.rarity
            current_prices[key].append(auction.unit_price)
        for key, prices in current_prices.items():
            self.lbin_stats[key].append(min(prices))

        self.update_lbin_calls += 1

        # Update every 15 calls
        if self.update_lbin_calls == 15:
            d = {}
            for key, prices in self.lbin_stats.items():
                d[key] = sum(prices) / len(prices)
            database.save_prices(d)

            # Reset
            self.update_lbin_calls = 0
            self.lbin_stats = defaultdict(list)


def setup(bot: Bot):
    bot.add_cog(AuctionHouseCog(bot))
