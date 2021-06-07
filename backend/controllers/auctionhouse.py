import asyncio
import inspect
import logging
from collections import defaultdict
from configparser import ConfigParser
from datetime import datetime, timedelta
from multiprocessing import Pool
from pathlib import Path
from typing import Awaitable, Callable, Dict, List, Optional, Tuple, Union

from backend.controllers.skyblockapi import SkyblockAPI
from backend.database import database
from models.auction import ActiveAuction, EndedAuction

_here = Path(__file__).parent
_cfg = ConfigParser()
_cfg.read(_here.parent.parent / 'config/spiggy.ini')

_aa_cfg = _cfg['Active Auctions']
AA_COOLDOWN = _aa_cfg.getfloat('Cooldown')
AA_MULTIPROCESS = _aa_cfg.getboolean('Multiprocess')
AA_BATCH_SIZE = _aa_cfg.getint('BatchSize')
AA_CLEAR_THRESHOLD = _aa_cfg.getint('ClearThreshold')

_ea_cfg = _cfg['Ended Auctions']
EA_COOLDOWN = _ea_cfg.getfloat('Cooldown')
EA_CLEAR_THRESHOLD = _ea_cfg.getint('ClearThreshold')


class AuctionHouse:
    """
    Class which abstracts auction-house related queries with item and auctions
    models.

    :ivar api: The Skyblock API wrapper to use.
    :ivar active_auctions: The most recent snapshot of active auctions.
    :ivar ended_auctions: The most recent page of ended auctions.
    :ivar _aa_handlers: The handlers for new active auctions.
    :ivar _ea_handlers: The handlers for new ended auctions.
    :ivar aa_last_update: The time when active_auctions was last updated.
    :ivar ea_last_update: The time when ended_auctions was last updated.

    :ivar aa_cache_count: Number of active auctions caches since last clear.
    :ivar ea_cache_count: Number of ended auctions caches since last clear.
    :ivar lbin_buffer: Map of items to lowest BIN prices.
    :ivar sold_buffer: Map of items to recently sold prices.
    :ivar active_occurrences:
    """
    api: SkyblockAPI
    active_auctions: List[ActiveAuction]
    ended_auctions: List[EndedAuction]
    _aa_handlers: List[Union[Callable, Awaitable]]
    _ea_handlers: List[Union[Callable, Awaitable]]
    aa_last_update: Optional[datetime]
    ea_last_update: Optional[datetime]

    aa_cache_count: int
    ea_cache_count: int
    active_occurrences: Dict[Tuple[str, str], int]
    lbin_buffer: Dict[Tuple[str, str], List[float]]
    sold_buffer: Dict[Tuple[str, str], List[float]]

    def __init__(self, api: SkyblockAPI) -> None:
        """
        Construct an AuctionHouse instance.

        :param api: The SkyblockAPI instance to use.
        :return: None.
        """
        self.api = api
        self.active_auctions, self.ended_auctions = [], []
        self._aa_handlers, self._ea_handlers = [], []
        self.aa_last_update, self.ea_last_update = None, None

        self.aa_cache_count, self.ea_cache_count = 0, 0
        self.active_occurrences = defaultdict(int)
        self.lbin_buffer = defaultdict(list)
        self.sold_buffer = defaultdict(list)

    async def cache_active_auctions(self) -> None:
        """
        Cache the active auctions and call the handler functions.
        Occasionally return control to the asyncio event loop between processing
        batches to minimize blocking.

        :return: None.
        """
        # Get the active auctions
        logging.info('Attempting cache')
        last_update, res = \
            await self.api.get_active_auctions()
        if last_update == self.aa_last_update:
            logging.info('Snapshot already cached, moving on')
            return

        # (Maybe) parse with multiprocessing
        logging.info('OK got proper snapshot')
        active_auctions = []
        if AA_MULTIPROCESS:
            with Pool() as p:
                for batch_start in range(0, len(res), AA_BATCH_SIZE):
                    batch_end = batch_start + AA_BATCH_SIZE
                    ext = p.map(ActiveAuction, res[batch_start:batch_end])
                    active_auctions.extend(ext)
                    await asyncio.sleep(0)
        else:
            for batch_start in range(0, len(res), AA_BATCH_SIZE):
                batch_end = batch_start + AA_BATCH_SIZE
                ext = [ActiveAuction(d)
                       for d in res[batch_start:batch_end]]
                active_auctions.extend(ext)
                await asyncio.sleep(0)

        # Parse and clean up
        active_auctions = [auction for auction in active_auctions if
                           auction.item.has_ascii_base_name()]

        # Update instance variables
        self.active_auctions = active_auctions
        self.aa_last_update = last_update
        self.aa_cache_count += 1

        # Notify the handlers
        logging.info('OK Successfully updated')
        for func in self._aa_handlers:
            if inspect.iscoroutinefunction(func):
                await func(last_update=self.aa_last_update,
                           active_auctions=self.active_auctions)
            else:
                func(last_update=self.aa_last_update,
                     active_auctions=self.active_auctions)

    async def cache_ended_auctions(self) -> None:
        """
        Cache the ended auctions and call the handler functions.

        :return: None.
        """
        logging.info('Attempting cache')
        last_update, res = \
            await self.api.get_ended_auctions()
        if last_update == self.ea_last_update:
            logging.info('Snapshot already cached, moving on')
            return

        # Parse and clean up
        ended_auctions = [EndedAuction(d) for d in res]
        ended_auctions = [auction for auction in ended_auctions if
                          auction.item.has_ascii_base_name()]

        # Update instance variables
        self.ended_auctions = ended_auctions
        self.ea_last_update = last_update
        self.ea_cache_count += 1

        # Notify the handlers
        logging.info('OK Successfully updated')
        for func in self._ea_handlers:
            if inspect.iscoroutinefunction(func):
                await func(last_update=self.ea_last_update,
                           ended_auctions=self.ended_auctions)
            else:
                func(last_update=self.ea_last_update,
                     ended_auctions=self.ended_auctions)

    def on_active_auctions(self, handler: Union[Callable, Awaitable]) -> None:
        """
        Add a handler to be called when new active auctions are found.

        :param handler: The handler to be added.
        :return: None.
        """
        self._aa_handlers.append(handler)

    def on_ended_auctions(self, handler: Union[Callable, Awaitable]) -> None:
        """
        Add a handler to be called when new ended auctions are found.

        :param handler: The handler to be added.
        :return: None.
        """
        self._ea_handlers.append(handler)

    async def start_aa_caching(self) -> None:
        """
        Start periodically caching active auctions.

        :return: None.
        """
        while True:
            await self.cache_active_auctions()
            await asyncio.sleep(AA_COOLDOWN)

    async def start_ea_caching(self) -> None:
        """
        Start periodically caching ended auctions.

        :return: None.
        """
        while True:
            await self.cache_ended_auctions()
            await asyncio.sleep(EA_COOLDOWN)

    async def start_caching(self) -> None:
        """
        Start periodically caching active and ended auctions.

        :return: None.
        """
        await asyncio.gather(self.start_aa_caching(), self.start_ea_caching())

    def update_active_buffers(self,
                              last_update: datetime,
                              active_auctions: List[ActiveAuction]) -> None:
        """
        Update the buffers from an active auctions snapshot.

        For each (item ID, rarity) pair, determine the number of times it
        appears and the lowest BIN which has been on the auction house for at
        least one minute.

        :param last_update: The timestamp of the snapshot.
        :param active_auctions: The active auctions snapshot.
        :return: None.
        """
        current_lbin = {}
        minute = timedelta(minutes=1)

        # Get current lowest BINs
        for auction in active_auctions:
            key = (auction.item.item_id, auction.item.rarity)
            self.active_occurrences[key] += 1
            duration = last_update - auction.start_time
            if auction.is_bin and duration >= minute:
                if key not in current_lbin:
                    current_lbin[key] = auction.unit_price
                else:
                    current_lbin[key] = min(current_lbin[key],
                                            auction.unit_price)

        # Insert into the buffer
        for key, price in current_lbin.items():
            self.lbin_buffer[key].append(price)

        # Maybe commit to database and clear the buffer
        if self.aa_cache_count == AA_CLEAR_THRESHOLD:
            database.save_lbin_history(self.lbin_buffer)
            self.aa_cache_count = 0
            self.active_occurrences = defaultdict(int)
            self.lbin_buffer = defaultdict(list)
            logging.info('OK Buffers committed to database and cleared')
        else:
            logging.info(f'OK Buffers updated '
                         f'[{self.aa_cache_count}/{AA_CLEAR_THRESHOLD}]')

    def update_ended_buffers(self,
                             ended_auctions: List[EndedAuction],
                             **kwargs) -> None:
        """
        Update the buffers from an ended auctions snapshot.

        :param ended_auctions: The ended auctions snapshot.
        :return: None.
        """
        for auction in ended_auctions:
            key = (auction.item.item_id, auction.item.rarity)
            self.sold_buffer[key].append(auction.unit_price)

        # Maybe commit to database and clear the buffer
        if self.ea_cache_count == EA_CLEAR_THRESHOLD:
            # TODO pass it to DB
            self.ea_cache_count = 0
            self.sold_buffer = defaultdict(list)
            logging.info('OK Buffers committed to database and cleared')
        else:
            logging.info(f'OK Buffers updated '
                         f'[{self.ea_cache_count}/{EA_CLEAR_THRESHOLD}]')


# Testing
if __name__ == '__main__':
    import dotenv
    import os

    root = Path(__file__).parent.parent.parent
    dotenv.load_dotenv(dotenv_path=root / 'config/.env')
    hypixel_key = os.getenv('HYPIXEL_API_KEY')

    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(funcName)s > %(levelname)s: '
                               '%(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')

    def print_aa_summary(last_update, active_auctions):
        print(f'Handler got {len(active_auctions)} active auctions at '
              f'{last_update}')

    def print_ea_summary(last_update, ended_auctions):
        print(f'Handler got {len(ended_auctions)} ended auctions at '
              f'{last_update}')

    async def main():
        async with SkyblockAPI(hypixel_key) as api:
            ah = AuctionHouse(api)
            ah.on_active_auctions(print_aa_summary)
            ah.on_ended_auctions(print_ea_summary)
            await ah.start_caching()

    asyncio.run(main())
