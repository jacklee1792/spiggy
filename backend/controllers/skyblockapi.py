from __future__ import annotations

import asyncio
import functools
import itertools
import logging
from collections import deque
from configparser import ConfigParser
from datetime import datetime, timedelta
from json import JSONDecodeError
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import requests
from aiohttp import ClientSession

from backend.exceptions import MalformedResponseError, ResponseCodeError, \
    UnexpectedUpdateError


_here = Path(__file__).parent
_cfg = ConfigParser()
_cfg.read(_here.parent.parent / 'config/spiggy.ini')

CACHE_MIN_DELAY = _cfg['AH Caching'].getfloat('CacheMinDelay')
CACHE_MAX_DELAY = _cfg['AH Caching'].getfloat('CacheMaxDelay')


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
        if res.status_code not in (200, 403):
            raise ResponseCodeError(res.status_code)
        try:
            body = res.json()
            if not body['success']:
                raise ValueError('Invalid Hypixel API key')
            self.limit = body['record']['limit'] - 20
        except (KeyError, JSONDecodeError):
            raise MalformedResponseError

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

    async def get_active_auctions(
            self,
            *args
    ) -> Tuple[datetime, List[Dict[str, Any]]]:
        """
        Attempts to get active auctions on the given pages, or all pages if no
        arguments are passed.

        :return: Pair containing the timestamp and the list of active auctions.
        """

        # Coroutine to get expected (total pages, timestamp)
        async def get_params() -> Tuple[int, datetime]:
            async with self._session.get(active_auctions_url(page=0)) as res:
                if res.status != 200:
                    raise ResponseCodeError(res.status)
                try:
                    body = await res.json()
                    return (
                        body['totalPages'],
                        datetime.fromtimestamp(body['lastUpdated'] / 1000)
                    )
                except (KeyError, JSONDecodeError):
                    raise MalformedResponseError

        page_count, expected_time = await get_params()
        time_lb = expected_time + timedelta(seconds=CACHE_MIN_DELAY)
        time_ub = expected_time + timedelta(seconds=CACHE_MAX_DELAY)
        time_now = datetime.now()

        # Already missed the window for this minute
        if time_now > time_ub:
            cache_time = time_lb + timedelta(seconds=60)
            logging.info(f'[API] Too late to cache active auctions for this'
                         f' minute, waiting until'
                         f' {cache_time.strftime("%-I:%M:%S %p")}'
                         f' to invoke cache')
            await asyncio.sleep((cache_time - time_now).total_seconds())
            page_count, expected_time = await get_params()
        # Not yet at the window for this minute, wait until then
        elif time_now < time_lb:
            logging.info(f'[API] Not enough time difference to cache active'
                         f' auctions yet, waiting until'
                         f' {time_lb.strftime("%-I:%M:%S %p")}'
                         f' to invoke cache')
            await asyncio.sleep((time_lb - time_now).total_seconds())

        logging.info(f'[API] Getting {page_count} pages of active auctions'
                     f' with timestamp'
                     f' {expected_time.strftime("%-I:%M:%S %p")}')

        # Coroutine to get the "auctions" field of a single page
        async def get_page(page: int) -> Dict[str, Any]:
            async with self._session.get(active_auctions_url(page=page)) as res:
                if res.status == 404:
                    logging.info(f'[API] Failed to get page {page}, got 404 '
                                 f'response')
                    raise UnexpectedUpdateError
                elif res.status != 200:
                    raise ResponseCodeError(res.status)
                try:
                    body = await res.json()
                    page_time = datetime.fromtimestamp(body['lastUpdated']
                                                       / 1000)
                    if page_time != expected_time:
                        logging.info(f'[API] Failed to get page {page},'
                                     f' got unexpected time of'
                                     f' {page_time.strftime("%-I:%M:%S %p")}')
                        raise UnexpectedUpdateError
                    return body['auctions']
                except (KeyError, JSONDecodeError):
                    raise MalformedResponseError

        # Get all pages
        page_numbers = list(args) or range(page_count)
        tasks = (get_page(page) for page in page_numbers)
        try:
            results = await asyncio.gather(*tasks)
            results_chained = list(itertools.chain.from_iterable(results))
            logging.info(f'[API] OK got {len(results_chained)} active auctions')
            return expected_time, results_chained
        except UnexpectedUpdateError:
            logging.info('[API] FAIL Could not get active auctions, trying'
                         ' again in 30 seconds')
            await asyncio.sleep(30)
            return await self.get_active_auctions(*page_numbers)

    async def get_ended_auctions(self) -> Tuple[datetime, List[Dict[str, Any]]]:
        """
        Get the recently ended auctions.

        :return: Pair containing the timestamp and the list of recently ended
        auctions.
        """
        logging.info('[API] Getting recently ended auctions')
        async with self._session.get(ENDED_AUCTIONS_URL) as res:
            if res.status != 200:
                raise ResponseCodeError(res.status)
            try:
                body = await res.json()
                last_updated = datetime.fromtimestamp(body['lastUpdated'] /
                                                      1000)
                auctions = body['auctions']
                logging.info(f'[API] OK got {len(auctions)} recently ended'
                             f' auctions')
                return last_updated, auctions
            except (KeyError, JSONDecodeError):
                raise MalformedResponseError

    async def get_bazaar(self) -> Tuple[datetime, Dict[str, Any]]:
        """
        Get data about bazaar products.

        :return: The JSON response.
        """
        logging.info('[API] Getting bazaar items')
        async with self._session.get(BAZAAR_URL) as res:
            if res.status != 200:
                raise ResponseCodeError(res.status)
            try:
                body = await res.json()
                last_updated = datetime.fromtimestamp(body['lastUpdated'] /
                                                      1000)
                products = body['products']
                logging.info(f'[API] OK got bazaar response')
                return last_updated, products
            except (KeyError, JSONDecodeError):
                raise MalformedResponseError


# Something to test the API wrapper with
if __name__ == '__main__':
    import aioconsole
    import dotenv
    import os
    from pathlib import Path

    root = Path(__file__).parent.parent.parent
    dotenv.load_dotenv(dotenv_path=root / 'config/.env')
    key = os.getenv('HYPIXEL_API_KEY')

    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(levelname)s: %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')

    async def main():
        async with SkyblockAPI(key) as api:
            while True:
                inp = await aioconsole.ainput('Enter a command: ')
                if inp == 'ended':
                    res = await api.get_ended_auctions()
                    print(str(res)[:100] + '...')
                elif inp == 'active':
                    res = await api.get_active_auctions()
                    print(str(res)[:100] + '...')
                elif inp == 'bazaar':
                    res = await api.get_bazaar()
                    print(str(res)[:100] + '...')
                await asyncio.sleep(3)

    asyncio.run(main())
