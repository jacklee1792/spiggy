import asyncio
import multiprocessing
import itertools
import inspect

from typing import Callable, List, Dict, Union, Coroutine, Optional
from aiohttp import ClientSession
from datetime import datetime, timedelta

from models.auction import ActiveAuction, EndedAuction

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
    recency_lower_bound: int
    recency_upper_bound: int
    batch_size: int
    check_delay: int
    observers: List[Union[Callable, Coroutine]]

    active_auctions: List[ActiveAuction]
    ended_auctions: List[EndedAuction]
    persisting_auctions: List[ActiveAuction]
    last_update: Optional[datetime]

    def __init__(self,
                 recency_lower_bound: int = 20,
                 recency_upper_bound: int = 40,
                 batch_size: int = 15000) -> None:
        """
        Construct an AuctionHouseObserver instance.

        :param recency_lower_bound: The minimum separation between the current
        time and the endpoint update to invoke caching.
        :param recency_upper_bound: The maximum separation between the current
        time and the endpoint update to invoke caching.
        :param batch_size: The number of active auction dictionaries to convert
        into ActiveAuction objects at once.
        :return: None.
        """
        self.recency_lower_bound = recency_lower_bound
        self.recency_upper_bound = recency_upper_bound
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

        last_update = datetime.fromtimestamp(res['lastUpdated'] / 1000)
        unexpected_update = self.last_update is not None \
                            and last_update != self.last_update
        if not res['success'] or unexpected_update:
            raise UnexpectedUpdateError('The Skyblock API updated while '
                                        'collecting data.')

        return res['auctions']

    async def check_new_auctions(self) -> None:
        """
        Check if the auctions endpoints have been updated recently. If they
        have, then create a list of auctions and pass to observers.

        The NBTFile library is quite slow, resulting in a slow ActiveAuction
        constructor. To avoid blocking bot functionality for long periods of
        time, this coroutine returns control to the event loop once a certain
        number of auctions are processed.

        :return: None.
        """

        # Check when the last endpoint update was
        async with ClientSession() as session:
            async with session.get(ACTIVE_AUCTIONS_ENDPOINT) as res:
                res = await res.json()
                last_update = datetime.fromtimestamp(res['lastUpdated'] / 1000)

        lb = timedelta(seconds=self.recency_lower_bound)
        ub = timedelta(seconds=self.recency_upper_bound)
        already_cached = self.last_update is not None \
                         and self.last_update == last_update

        if lb <= datetime.now() - last_update <= ub and not already_cached:
            self.last_update = last_update
        else:
            return

        # Get the active auctions
        page_count = res['totalPages']
        tasks = [self._get_active_auctions_page(page)
                 for page in range(1, page_count)]
        try:
            responses = await asyncio.gather(*tasks)
        except UnexpectedUpdateError:
            return

        responses = list(itertools.chain.from_iterable(responses))

        # Parse with multiprocessing
        active_auctions = []
        with multiprocessing.Pool() as p:
            batch_start = 0
            while batch_start < len(responses):
                batch_end = batch_start + self.batch_size
                ext = p.map(ActiveAuction, responses[batch_start:batch_end])
                active_auctions.extend(ext)
                # Batch is done, briefly return control to event loop
                batch_start = batch_end
                await asyncio.sleep(1)

        # Get the ended auctions
        async with ClientSession() as session:
            async with session.get(ENDED_AUCTIONS_ENDPOINT) as res:
                res = await res.json()
        ended_auctions = list(map(EndedAuction, res['auctions']))

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
