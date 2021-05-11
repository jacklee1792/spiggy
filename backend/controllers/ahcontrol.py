import asyncio
import multiprocessing
import itertools
import inspect

from typing import Callable, List, Dict, Union, Coroutine
from aiohttp import ClientSession
from datetime import datetime, timedelta

from models.auction import ActiveAuction, EndedAuction

ACTIVE_AUCTIONS_ENDPOINT = 'https://api.hypixel.net/skyblock/auctions'
ENDED_AUCTIONS_ENDPOINT = 'https://api.hypixel.net/skyblock/auctions_ended'


class SkyblockAPIError(Exception):
    pass


class UnexpectedUpdateError(Exception):
    pass


class AuctionHouseControl:
    """
    Controller which wraps some of the operations associated with querying the
    Skyblock API.
    """
    recency_lower_bound: int
    recency_upper_bound: int
    auctions_last_fetch: datetime
    batch_size: int
    check_delay: int
    observers: List[Union[Callable, Coroutine]]

    def __init__(self,
                 recency_lower_bound: int = 20,
                 recency_upper_bound: int = 40,
                 batch_size: int = 15000,
                 check_delay: int = 2) -> None:
        """
        Construct an AuctionHouseControl instance.

        :param recency_lower_bound: The minimum separation between the current
        time and the endpoint update to invoke caching.
        :param recency_upper_bound: The maximum separation between the current
        time and the endpoint update to invoke caching.
        :param batch_size: The number of active auction dictionaries to convert
        into ActiveAuction objects at once.
        :param check_delay: How often a check for new auctions is performed.
        :return: None.
        """
        self.recency_lower_bound = recency_lower_bound
        self.recency_upper_bound = recency_upper_bound
        self.auctions_last_fetch = datetime.now()
        self.batch_size = batch_size
        self.check_delay = check_delay
        self.observers = []

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
        if last_update != self.auctions_last_fetch:
            print(last_update, self.auctions_last_fetch)
            raise UnexpectedUpdateError

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

        if lb <= datetime.now() - last_update <= ub:
            self.auctions_last_fetch = last_update
        else:
            return

        # Get the active auctions
        page_count = res['totalPages']
        tasks = [self._get_active_auctions_page(page)
                 for page in range(1, page_count)]
        responses = await asyncio.gather(*tasks)
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
                print(f'batch starting at {batch_start} done')
                batch_start = batch_end
                await asyncio.sleep(1)

        # Get the ended auctions
        async with ClientSession() as session:
            async with session.get(ENDED_AUCTIONS_ENDPOINT) as res:
                res = await res.json()
        ended_auctions = list(map(EndedAuction, res['auctions']))

        # Notify the observers
        for func in self.observers:
            if inspect.iscoroutinefunction(func):
                await func(active_auctions=active_auctions,
                           ended_auctions=ended_auctions)
            else:
                func(active_auctions=active_auctions,
                     ended_auctions=ended_auctions)

    def add_observer(self, func: Union[Callable, Coroutine]) -> None:
        """
        Add a callable which observes updates in the active/ended auction
        endpoints. When an update is detected, each observer will be called
        with keyword arguments <active_auctions> and <ended_auctions>.

        :param func: The callable to be added as an observer.
        :return: None.
        """
        self.observers.append(func)

    async def start_checking(self) -> None:
        """
        Start checking occasionally for new auctions.

        :return: None.
        """
        while True:
            await self.check_new_auctions()
            await asyncio.sleep(self.check_delay)


if __name__ == '__main__':

    # Testing if AuctionHouseControl returns control to the event loop properly
    # and runs all observers as expected

    def f(active_auctions, ended_auctions):
        print(f'got something at {datetime.now()}')
        la = len(active_auctions)
        le = len(ended_auctions)
        print(f'there are {la} active, {le} ended')

    def g(active_auctions, ended_auctions):
        ids = [auction.auction_id for auction in active_auctions]
        assert len(ids) == len(set(ids))
        print('OK ids are distinct')

    async def spam():
        while True:
            print('spam')
            await asyncio.sleep(0.5)

    ahc = AuctionHouseControl()
    ahc.add_observer(f)
    ahc.add_observer(g)

    async def bot():
        await asyncio.gather(ahc.start_checking(), spam())

    asyncio.run(bot())
