from __future__ import annotations

import asyncio
import functools
import itertools
import logging
import math
from collections import deque
from configparser import ConfigParser
from datetime import datetime, timedelta
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Callable, Dict, List, Literal, Optional, Tuple

import requests
from aiohttp import ClientSession

from backend.exceptions import ResponseCodeError, UnexpectedUpdateError


_here = Path(__file__).parent
_cfg = ConfigParser()
_cfg.read(_here.parent.parent / 'config/spiggy.ini')

AA_IDEAL_DELAY = _cfg['Active Auctions'].getfloat('IdealDelay')
EA_IDEAL_DELAY = _cfg['Ended Auctions'].getfloat('IdealDelay')
BZ_IDEAL_DELAY = _cfg['Bazaar'].getfloat('IdealDelay')


def key_info_url(key: str) -> str:
    """
    Get the URL for the key endpoint with the key parameter filled in.

    :param key: The given key.
    :return: The corresponding URL.
    """
    return f'https://api.hypixel.net/key?key={key}'


def active_auctions_url(page: int) -> str:
    """
    Get the URL for the active auctions endpoint with the page parameter filled
    in.

    :param page: The given page number.
    :return: The corresponding URL.
    """
    return f'https://api.hypixel.net/skyblock/auctions?page={page}'


ENDED_AUCTIONS_URL = 'https://api.hypixel.net/skyblock/auctions_ended'
BAZAAR_URL = 'https://api.hypixel.net/skyblock/bazaar'


def use_key(req: Callable) -> Callable:
    """
    Decorator to rate-limit API calls over a one-minute window, uses the
    "leaky bucket" technique.

    :param req: The request to be wrapped.
    :return: The wrapped request.
    """
    @functools.wraps(req)
    async def wrapper(self, *args, **kwargs):
        now = datetime.now()
        minute = timedelta(minutes=1)

        # Pop ones that are no longer in the minute window
        while len(self.key_calls) and now - self.key_calls[0] > minute:
            self.key_calls.popleft()

        # Schedule the current request
        scheduled_time = now if len(self.key_calls) < self.limit \
            else self.key_calls[-self.limit] + minute
        self.key_calls.append(scheduled_time)
        await asyncio.sleep((scheduled_time - now).total_seconds())
        return await req(self, *args, **kwargs)
    return wrapper


class SkyblockAPI:
    """
    Async wrapper for the Skyblock API with rate-limiting. Serves JSON in the
    form of dictionaries.

    The class takes all non-200 responses as invalid, and will make a GET
    attempt every 30 seconds until a 200 response is received.

    :ivar _session: The session which is used for HTTPS requests.
    :ivar api_key: The API key to use for requests which require it.
    :ivar key_calls: The timestamps of key-authenticated API calls from the
    past minute.
    :ivar limit: The number of key-authenticated API calls allowed per minute.
    """
    _session: ClientSession
    api_key: str
    key_calls: deque[datetime]
    limit: int

    def __init__(self, api_key: str):
        """
        Construct an API wrapper instance from an API key.

        :param api_key: A Hypixel API key.
        :return: None.
        """
        self.api_key = api_key
        self.key_calls = deque()
        res = requests.get(key_info_url(key=self.api_key))

        body = res.json()
        if not body['success']:
            raise ValueError('Invalid Hypixel API key')
        self.limit = body['record']['limit'] - 20

    async def __aenter__(self) -> SkyblockAPI:
        """
        Enter the session.

        :return: None.
        """
        self._session = ClientSession()
        return self

    async def __aexit__(self, *args) -> None:
        """
        Close the session.

        :return: None.
        """
        await self._session.close()

    async def get_active_auctions(self) \
            -> Tuple[datetime, List[Dict[str, Any]]]:
        """
        Get a snapshot of /auctions at the earliest possible "ideal" time.

        :return: Pair containing the lastUpdated timestamp and the
        corresponding list of active auctions.
        """
        logging.debug('Attempting to get active auctions snapshot')
        page0_last_update: Optional[datetime] = None

        # Coroutine to get a single page and raise an exception if something
        # goes wrong
        async def get_page(page: int) -> Dict[str, Any]:
            async with self._session.get(active_auctions_url(page=page)) as res:
                if res.status != 200:
                    raise ResponseCodeError
                body = await res.json()
                last_update = datetime.fromtimestamp(body['lastUpdated'] / 1000)
                if (page0_last_update is not None
                        and last_update != page0_last_update):
                    msg = f'Expected ' \
                          f'{page0_last_update.strftime("%-I:%M:%S %p")} but ' \
                          f'got {last_update.strftime("%-I:%M:%S %p")} on ' \
                          f'page {page}'
                    raise UnexpectedUpdateError(msg)
                return body

        # Get the page count and the page 0 lastUpdated field
        try:
            page0 = await get_page(0)
            page_count = page0['totalPages']
            page0_last_update = datetime.fromtimestamp(page0['lastUpdated']
                                                       / 1000)
        except (ResponseCodeError, UnexpectedUpdateError):
            logging.exception('FAIL Could not get page 0, will try '
                              'again in 30 seconds')
            await asyncio.sleep(30)
            return await self.get_active_auctions()

        # Wait until ideal time
        now_time = datetime.now()
        ideal_time = page0_last_update + timedelta(seconds=AA_IDEAL_DELAY)

        # If ideal time is already passed, try to get the next snapshot
        if now_time > ideal_time:
            diff_minutes = (now_time - ideal_time).total_seconds() / 60
            delta = timedelta(minutes=math.ceil(diff_minutes))
            page0_last_update += delta
            ideal_time += delta
        logging.info(f'Waiting until next ideal time '
                     f'{ideal_time.strftime("%-I:%M:%S %p")} to capture '
                     f'snapshot with timestamp '
                     f'{page0_last_update.strftime("%-I:%M:%S %p")}')
        await asyncio.sleep((ideal_time - now_time).total_seconds())

        # Get a snapshot
        try:
            tasks = (get_page(p) for p in range(page_count))
            bodies = await asyncio.gather(*tasks)
            auctions = list(itertools.chain.from_iterable(
                body['auctions'] for body in bodies
            ))
            logging.debug(f'OK got active auctions snapshot with timestamp '
                          f'{page0_last_update.strftime("%-I:%M:%S %p")}')
            return page0_last_update, auctions
        except (ResponseCodeError, UnexpectedUpdateError):
            logging.exception('FAIL Could not get snapshot, will try '
                              'for new snapshot in 30 seconds')
            await asyncio.sleep(30)
            return await self.get_active_auctions()

    async def get_ended_auctions(self) -> Tuple[datetime, List[Dict[str, Any]]]:
        """
        Get the recently ended auctions at the earliest possible "ideal" time.

        :return: Pair containing the timestamp and the list of recently ended
        auctions.
        """
        logging.debug('Attempting to get ended auctions')
        async with self._session.get(ENDED_AUCTIONS_URL) as res:
            if res.status != 200:
                logging.debug('FAIL could not get ended auctions, will try '
                              'again in 30 seconds')
                await asyncio.sleep(30)
                return await self.get_active_auctions()
            body = await res.json()
            last_update = datetime.fromtimestamp(body['lastUpdated'] / 1000)
            auctions = body['auctions']
            logging.debug(f'OK got ended auctions with timestamp '
                          f'{last_update.strftime("%-I:%M:%S %p")}')
            return last_update, auctions

    async def get_bazaar_products(self) -> Tuple[datetime, Dict[str, Any]]:
        """
        Get the bazaar products at the earliest possible "ideal" time.

        :return: Pair containing the timestamp and a dict containing bazaar
        products.
        """
        logging.debug('Attempting to get bazaar products')
        async with self._session.get(BAZAAR_URL) as res:
            if res.status != 200:
                logging.debug('FAIL could not get bazaar products, will try '
                              'again in 30 seconds')
                await asyncio.sleep(30)
                return await self.get_bazaar_products()
            body = await res.json()
            last_update = datetime.fromtimestamp(body['lastUpdated'] / 1000)
            products = body['products']
            logging.debug(f'OK got bazaar products with timestamp '
                          f'{last_update.strftime("%-I:%M:%S %p")}')
            return last_update, products


# Something to test the API wrapper with
if __name__ == '__main__':
    import aioconsole
    import dotenv
    import os
    from pathlib import Path

    root = Path(__file__).parent.parent.parent
    dotenv.load_dotenv(dotenv_path=root / 'config/.env')
    key = os.getenv('HYPIXEL_API_KEY')

    logging.basicConfig(level=logging.DEBUG,
                        format='[%(asctime)s] %(name)s > %(levelname)s: '
                               '%(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')

    async def main():
        async with SkyblockAPI(key) as api:
            while True:
                inp = (await aioconsole.ainput('Enter a command: ')).split()
                if inp[0] == 'ended':
                    t, auctions = await api.get_ended_auctions()
                    print(f'OK got {len(auctions)} items at {t}')
                    print(str(auctions)[:100] + '...')
                elif inp[0] == 'active':
                    t, auctions = await api.get_active_auctions()
                    print(f'OK got {len(auctions)} items at {t}')
                    print(str(auctions)[:100] + '...')
                elif inp[0] == 'bazaar':
                    t, products = await api.get_bazaar_products()
                    print(f'OK got {len(products)} products at {t}')
                    print(str(products)[:100] + '...')
                await asyncio.sleep(3)

    asyncio.run(main())
