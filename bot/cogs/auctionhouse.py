import logging

from discord.ext import commands, tasks
from typing import List, Dict, Any, Tuple
from backend.database import database
from backend.parsing import nbtparse, styling
from aiohttp import ClientSession

ENDED_PAGECOUNT_LIMIT = 1

class AuctionHouse(commands.Cog):

    bot: commands.Bot
    database: database.SpiggyDatabase
    ended_last_updated: int
    ended_buffer: List[Tuple[str, str, int]]
    ended_pagecount: int

    def __init__(self, bot):
        self.bot = bot
        self.database = database.SpiggyDatabase('database.db')
        self.ended_last_updated = 0
        self.ended_buffer = []
        self.ended_buffer_pagecount = 0
        self.check_ended.start()

    async def _record_ended(self, auctions: List[Dict[Any, Any]]) -> None:
        """
        Insert a list of auctions in the form (item_id, basename, price) into
        the buffer, and record to database if enough pages are already in the
        buffer. Filter out any unwanted items before writing to buffer.

        :param auctions: the list of auctions to be recorded.
        :return: None.
        """

        for auction in auctions:
            item_nbt = nbtparse.deserialize(auction['item_bytes'])
            hy_id = nbtparse.extract_id(item_nbt)
            rarity = nbtparse.extract_rarity(item_nbt)
            price = auction['price']
            if hy_id == 'RUNE':
                rune, lvl = nbtparse.extract_rune(item_nbt)
                item_id = f'{rune}_{lvl}_RUNE'
                self.ended_buffer.append((item_id, rarity, price))
            elif hy_id == 'ENCHANTED_BOOK':
                enchants = nbtparse.extract_enchants(item_nbt)
                if len(enchants) == 1:
                    enchant, lvl = enchants[0]
                    item_id, _ = styling.get_book_id_basename(enchant, lvl)
                    self.ended_buffer.append((item_id, rarity, price))
            elif hy_id == 'PET':
                # TODO: handle this separately
                pass
            elif hy_id != 'POTION':
                self.ended_buffer.append((hy_id, rarity, price))

        logging.info(f'OK, page added to ended auctions buffer')
        self.ended_buffer_pagecount += 1

        if self.ended_buffer_pagecount >= ENDED_PAGECOUNT_LIMIT:
            logging.info('Write buffer to database')
            db = database.SpiggyDatabase('database.db')
            db.cache_ended_auctions(self.ended_buffer)
            db.commit_changes()
            self.ended_buffer.clear()
            self.ended_buffer_pagecount = 0


    @tasks.loop(seconds=30)
    async def check_ended(self) -> None:
        """
        Periodically check for new recently ended auctions pages.

        :return: None.
        """

        logging.info('Checking for new ended auctions')

        async with ClientSession() as session:
            url = 'https://api.hypixel.net/skyblock/auctions_ended'
            async with session.get(url) as res:
                res_json = await res.json()
                if res_json['lastUpdated'] == self.ended_last_updated:
                    logging.info(f'Current ended auctions page '
                                 f'({self.ended_last_updated}) already cached')
                else:
                    self.ended_last_updated = res_json['lastUpdated']
                    await self._record_ended(res_json['auctions'])


def setup(bot):
    bot.add_cog(AuctionHouse(bot))
    logging.info('AuctionHouse cog added to bot')
