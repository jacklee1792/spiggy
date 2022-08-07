import asyncio
import inspect
import logging
from configparser import ConfigParser
from datetime import datetime
from pathlib import Path
from typing import Awaitable, Callable, List, Optional, Union

from backend.skyblockapi import SkyblockAPI
from models.bazaarproduct import BazaarProduct

_here = Path(__file__).parent
_cfg = ConfigParser()
_cfg.read(_here.parent.parent / 'config/spiggy.ini')

BZ_COOLDOWN = _cfg['Bazaar'].getfloat('Cooldown')


class Bazaar:
    """
    Class which abstracts bazaar-related queries.

    :ivar api: The Skyblock API wrapper to use.
    :ivar products: List containing the most recent bazaar product info.
    """
    api: SkyblockAPI
    products: List[BazaarProduct]
    _handlers: List[Union[Callable, Awaitable]]
    last_update: Optional[datetime]

    def __init__(self, api: SkyblockAPI) -> None:
        self.api = api
        self.products = []
        self._handlers = []
        self.last_update = None

    async def cache_products(self) -> None:
        """
        Cache the bazaar products and call the handler functions.

        :return: None.
        """
        logging.info('Attempting cache')
        last_update, res = await self.api.get_bazaar_products()
        if last_update == self.last_update:
            logging.info('Snapshot already cached, moving on')
            return

        # Parse
        products = [BazaarProduct(item_id, d) for item_id, d in res.items()]

        # Update instance variables
        self.products = products
        self.last_update = last_update

        # Notify the handlers
        for func in self._handlers:
            if inspect.iscoroutinefunction(func):
                await func(last_update=self.last_update,
                           products=self.products)
            else:
                func(last_update=self.last_update,
                     products=self.products)

    def on_products(self, handler: Union[Callable, Awaitable]) -> None:
        """
        Add a handler to be called when new product information is found.

        :param handler: The handler to be added.
        :return: None.
        """
        self._handlers.append(handler)

    async def start_caching(self) -> None:
        """
        Start periodically caching bazaar product information.

        :return: None.
        """
        while True:
            await self.cache_products()
            await asyncio.sleep(BZ_COOLDOWN)


if __name__ == '__main__':
    import dotenv
    import os

    root = Path(__file__).parent.parent.parent
    dotenv.load_dotenv(dotenv_path=root / 'config/.env')
    key = os.getenv('HYPIXEL_API_KEY')

    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(funcName)s > %(levelname)s: '
                               '%(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')

    def print_bz_summary(last_update, products):
        print('OK', last_update, len(products))

    async def main():
        async with SkyblockAPI(key) as api:
            bz = Bazaar(api)
            bz.on_products(print_bz_summary)
            await bz.start_caching()

    asyncio.run(main())
