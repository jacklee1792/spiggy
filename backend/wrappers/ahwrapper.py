import asyncio

from typing import Callable, Any, List
from aiohttp import ClientSession

from models.auction import ActiveAuction
from models.user import User

ACTIVE_AUCTIONS_ENDPOINT = 'https://api.hypixel.net/skyblock/auctions'
ENDED_AUCTIONS_ENDPOINT = 'https://api.hypixel.net/skyblock/auctions_ended'

_active_auctions_last_update = None
_ended_auctions_last_update = None
_active_auctions_on_update_processes = []
_ended_auctions_on_update_processes = []
_check_active_auctions_batch_size = 10


def on_active_auctions_update(func: Callable[[Any], Any]) -> None:
    """
    Add a process to be executed when the active auctions page updates.

    :param func: a callable with no positional arguments which can optionally
    take the list of active auctions as 'active_auctions'.
    :return: None.
    """
    _active_auctions_on_update_processes.append(func)


def on_ended_auctions_update(func: Callable[[Any], Any]) -> None:
    """
    Add a process to be executed when the ended auctions page updates.

    :param func: a callable with no positional arguments which can optionally
    take the list of ended auctions as 'ended_auctions'.
    :return: None.
    """
    _ended_auctions_on_update_processes.append(func)


async def get_active_auctions_page(page: int) -> List[ActiveAuction]:
    """
    Given a page number, return the list of active auctions on that page. As
    well, ensure that the lastUpdated field matches (that is, the API didn't
    update before this coroutine was called).

    Return an empty list if that check fails, or the page doesn't exist.

    :param page: The page number of active auctions to be retrieved.
    :return: The list of active auctions on the given page.
    """
    global _active_auctions_last_update

    print(f'checking page {page}')
    url = ACTIVE_AUCTIONS_ENDPOINT + f'?page={page}'
    async with ClientSession() as session:
        async with session.get(url) as res:
            res = await res.json()

            if not res['success'] or res['lastUpdated'] \
                    != _active_auctions_last_update:
                return []

            return [ActiveAuction(d) for d in res['auctions']]


async def check_active_auctions() -> None:
    """
    Check if active auctions has been updated. If it has, then get a list of
    active auctions and pass it to the functions which are listening for an
    update.

    :return: None.
    """
    global _active_auctions_last_update
    global _active_auctions_on_update_processes

    async with ClientSession() as session:
        async with session.get(ACTIVE_AUCTIONS_ENDPOINT) as res:
            res = await res.json()
            if _active_auctions_last_update != res['lastUpdated']:
                _active_auctions_last_update = res['lastUpdated']
                auctions = []
                page = 1
                while True:
                    # Try to batch pages together
                    coros = (get_active_auctions_page(page + i) for i in
                             range(_check_active_auctions_batch_size))
                    results = await asyncio.gather(*coros)
                    if not results[0]:
                        break
                    for ext in results:
                        auctions.extend(ext)
                    page += _check_active_auctions_batch_size
                for process in _active_auctions_on_update_processes:
                    process(auctions)


if __name__ == '__main__':
    # Playing with the "check for gaps" auction flipping idea,
    # might implement this formally later
    from collections import defaultdict

    # "Candidates" from the previous round
    candidates = []

    # Some constraints
    gap_required = 200000
    max_price = 5000000

    def check_gaps(auctions: List[ActiveAuction]) -> None:
        global candidates

        mappings = defaultdict(list)
        active_ids = set()

        bin_auctions = list(filter(
            lambda a: a.is_bin,
            auctions
        ))
        for auction in bin_auctions:
            item = auction.item
            mappings[item.item_id].append(auction)
            active_ids.add(auction.auction_id)

        # Check if there are any good candidates from the previous round that
        # are still around
        for auction, gap in candidates:
            if auction.auction_id in active_ids:
                item_name = auction.item.base_name
                buy_price = auction.starting_price
                # Filter out some garbage
                if gap / buy_price < 0.2:
                    ign = auction.seller.username
                    print(f'/ah {ign}, buy {item_name} for {buy_price}, '
                          f'expected profit is {gap}')

        # Clear the old candidates
        candidates = []

        # Find more candidates
        for item_id, lst in mappings.items():
            lst.sort(key=lambda a: a.starting_price)
            if len(lst) > 1 and lst[0].starting_price <= max_price:
                gap = lst[1].starting_price - lst[0].starting_price
                if gap >= gap_required:
                    good_auction = lst[0]
                    candidates.append((good_auction, gap))
        print(f'found {len(candidates)} new candidates this round')

    # Make this callable run every time there's a new list of auctions
    on_active_auctions_update(check_gaps)

    # Check every once in a while
    async def repeatedly_check() -> None:
        while True:
            print('checking for new active auctions...')
            await check_active_auctions()
            await asyncio.sleep(5)

    # :D
    asyncio.run(repeatedly_check())
