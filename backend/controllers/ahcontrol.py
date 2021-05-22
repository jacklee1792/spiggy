import asyncio
import inspect
import itertools
from configparser import ConfigParser
from datetime import datetime, timedelta
from multiprocessing import Pool
from pathlib import Path
from typing import Callable, Coroutine, Dict, List, Optional, Union

from aiohttp import ClientSession

from models.auction import ActiveAuction, EndedAuction


_here = Path(__file__).parent
_cfg = ConfigParser()
_cfg.read(_here.parent.parent / 'config/spiggy.ini')

CACHE_MIN_DELAY = _cfg['AH Caching'].getfloat('CacheMinDelay')
CACHE_MAX_DELAY = _cfg['AH Caching'].getfloat('CacheMaxDelay')
CACHE_COOLDOWN = _cfg['AH Caching'].getfloat('CacheCooldown')
CACHE_COOLDOWN_TD = timedelta(minutes=CACHE_COOLDOWN) - timedelta(seconds=1)
PROCESSING_BATCH_SIZE = _cfg['AH Caching'].getint('ProcessingBatchSize')
BATCH_DELAY = _cfg['AH Caching'].getfloat('BatchDelay')
USE_MULTIPROCESSING = _cfg['AH Caching'].getboolean('UseMultiprocessing')

ACTIVE_AUCTIONS_ENDPOINT = 'https://api.hypixel.net/skyblock/auctions'
ENDED_AUCTIONS_ENDPOINT = 'https://api.hypixel.net/skyblock/auctions_ended'


class UnexpectedUpdateError(Exception):
    pass


class AuctionHouseObserver:
    """
    This class wraps some of the operations associated with querying the
    Skyblock API. It stores the most recent auctions related data as
    instance variables, and supports "refreshing" through check_new_auctions.
    """
    cache_min_delay: float
    cache_max_delay: float
    batch_size: int
    check_delay: int
    observers: List[Union[Callable, Coroutine]]

    active_auctions: List[ActiveAuction]
    ended_auctions: List[EndedAuction]
    persisting_auctions: List[ActiveAuction]
    last_update: Optional[datetime]

    def __init__(self,
                 cache_min_delay: int = CACHE_MIN_DELAY,
                 cache_max_delay: int = CACHE_MAX_DELAY,
                 batch_size: int = PROCESSING_BATCH_SIZE) -> None:
        """
        Construct an AuctionHouseObserver instance.

        :param cache_min_delay: The minimum separation between the current
        time and the endpoint update to invoke caching.
        :param cache_max_delay: The maximum separation between the current
        time and the endpoint update to invoke caching.
        :param batch_size: The number of active auction dictionaries to convert
        into ActiveAuction objects at once.
        :return: None.
        """
        self.cache_min_delay = cache_min_delay
        self.cache_max_delay = cache_max_delay
        self.batch_size = batch_size

        self.last_update = None
        self.observers = []
        self.active_auctions = []
        self.ended_auctions = []
        self.persisting_auctions = []

    async def _get_active_auctions_page(self, page: int) -> List[Dict]:
        """
        Return the auctions on the given page as a list of dictionaries.

        :param page: The number of the page to be read.
        :return: The auctions on the given page, as an unparsed list.
        """

        async with ClientSession() as session:
            url = ACTIVE_AUCTIONS_ENDPOINT + f'?page={page}'
            async with session.get(url) as res:
                res = await res.json()

        if not res['success']:
            print(f'res success false on page {page}')
            raise UnexpectedUpdateError

        last_update = datetime.fromtimestamp(res['lastUpdated'] / 1000)
        unexpected_update = self.last_update is not None \
            and last_update != self.last_update
        if unexpected_update:
            print(f'unexpected update on page {page}'
                  f' (expected {self.last_update.strftime("%-I:%M:%S %p")}'
                  f' but got {last_update.strftime("%-I:%M:%S %p")})')
            raise UnexpectedUpdateError

        return res['auctions']

    async def check_new_auctions(self) -> None:
        """
        Cache auctions from the API if the conditions to do so are met.

        :return: None.
        """
        # Check when the last endpoint update was
        async with ClientSession() as session:
            async with session.get(ACTIVE_AUCTIONS_ENDPOINT) as res:
                res = await res.json()
                try:
                    api_last_update = datetime.fromtimestamp(
                        res['lastUpdated'] / 1000)
                # Maybe getting rate-limited?
                except KeyError:
                    return

        lb = timedelta(seconds=self.cache_min_delay)
        ub = timedelta(seconds=self.cache_max_delay)
        enough_delay = self.last_update is None \
            or self.last_update + CACHE_COOLDOWN_TD <= api_last_update

        # Check that the conditions are met
        if lb <= datetime.now() - api_last_update <= ub and enough_delay:
            self.last_update = api_last_update
            await self.cache_auctions(page_count=res['totalPages'])

    async def cache_auctions(self, page_count: int) -> None:
        """
        Cache the active and ended auctions and call the observer functions.
        Occasionally return control to the asyncio event loop between processing
        batches to minimize blocking.

        This coroutine also works under the assumption that there is exactly one
        page of (<=1000) of ended auctions.

        :param page_count: The number of expected active auctions pages
        :return: None.
        """
        # Get the active auctions
        print(f'[{datetime.now()}] trying to cache {page_count} pages')
        tasks = [self._get_active_auctions_page(page)
                 for page in range(1, page_count)]
        try:
            responses = await asyncio.gather(*tasks)
        except UnexpectedUpdateError:
            return

        responses = list(itertools.chain.from_iterable(responses))
        print(f'[{datetime.now()}] OK got API response')

        # (Maybe) parse with multiprocessing
        active_auctions = []
        if USE_MULTIPROCESSING:
            with Pool() as p:
                batch_start = 0
                while batch_start < len(responses):
                    batch_end = batch_start + self.batch_size
                    ext = p.map(ActiveAuction, responses[batch_start:batch_end])
                    active_auctions.extend(ext)
                    batch_start = batch_end
                    await asyncio.sleep(BATCH_DELAY)
        else:
            batch_start = 0
            while batch_start < len(responses):
                batch_end = batch_start + self.batch_size
                ext = [ActiveAuction(d)
                       for d in responses[batch_start:batch_end]]
                active_auctions.extend(ext)
                batch_start = batch_end
                await asyncio.sleep(BATCH_DELAY)

        # Get the ended auctions
        async with ClientSession() as session:
            async with session.get(ENDED_AUCTIONS_ENDPOINT) as res:
                res = await res.json()
        ended_auctions = list(map(EndedAuction, res['auctions']))

        # Clean up the auctions with malformed items
        active_auctions = [auction for auction in active_auctions if
                           auction.item is not None]
        ended_auctions = [auction for auction in ended_auctions if
                          auction.item is not None]

        print(f'[{datetime.now()}] OK done casting to models')

        # Figure out which auctions persisted from the last round
        previous_ids = {auction.auction_id for auction in self.active_auctions}
        self.persisting_auctions = [auction for auction in active_auctions if
                                    auction.auction_id in previous_ids]

        # Update with new active and ended auctions
        self.active_auctions = active_auctions
        self.ended_auctions = ended_auctions

        # Notify the observers
        for func in self.observers:
            if inspect.iscoroutinefunction(func):
                await func()
            else:
                func()

    def add_observer(self, func: Union[Callable, Coroutine]) -> None:
        """
        Add a callable or coroutine to be called with no arguments whenever
        new auctions are cached.

        :param func: The callable or coroutine to be added as an observer.
        :return: None.
        """
        self.observers.append(func)
