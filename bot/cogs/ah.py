from discord import TextChannel
from discord.ext import commands, tasks
from discord.ext.commands import Bot, Cog
from discord.ext.commands.context import Context
from datetime import datetime, timezone

from backend.controllers.ahcontrol import AuctionHouseControl
from typing import List, Optional
from models.auction import ActiveAuction, EndedAuction


class AuctionHouseCog(Cog):
    """
    Bot cog which handles auction commands.
    """
    bot: Bot
    ahc: AuctionHouseControl
    active_auctions: List[ActiveAuction]

    def __init__(self, bot: Bot) -> None:
        """
        Initialize the cog.

        :param bot: The bot object which holds this cog.
        """
        self.bot = bot
        self.ahc = AuctionHouseControl()
        self.active_auctions = []
        self.ahc.add_observer(self.notify_update)
        self.ahc.add_observer(self.update_active_auctions)
        self.check_new_auctions.start()

    @commands.command()
    async def lbin(self, ctx: Context, item_id: str):
        if not self.active_auctions:
            return await ctx.send('No active auctions cached!')
        else:
            def is_match(auction: ActiveAuction):
                return auction.item.item_id == item_id and auction.is_bin
            matches = [auction for auction in self.active_auctions
                       if is_match(auction)]
            matches.sort(key=lambda a: a.price)
            matches = matches[:5]
            for match in matches:
                await ctx.send(f'{match.seller.username} {match.price}')

    @commands.command()
    async def endsoon(self, ctx: Context, item_id: str):
        if not self.active_auctions:
            return await ctx.send('No active auctions cached!')
        else:
            def is_match(auction: ActiveAuction):
                return auction.item.item_id == item_id and not auction.is_bin
            matches = [auction for auction in self.active_auctions
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
        Check for new auctions on the ahc object.

        :return: None.
        """
        if self.dump_channel:
            await self.dump_channel.send('Checking for new auctions...')
        await self.ahc.check_new_auctions()

    def update_active_auctions(self,
                               active_auctions: List[ActiveAuction],
                               **kwargs) -> None:
        self.active_auctions = active_auctions

    async def notify_update(self,
                            active_auctions: List[ActiveAuction],
                            ended_auctions: List[EndedAuction]) -> None:
        """
        Notify the dump channel about new auctions.

        :return: None.
        """
        if self.dump_channel:
            la = len(active_auctions)
            le = len(ended_auctions)
            await self.dump_channel.send(f'Found {la} new active auctions and'
                                         f' {le} new ended auctions')


def setup(bot: Bot):
    bot.add_cog(AuctionHouseCog(bot))
