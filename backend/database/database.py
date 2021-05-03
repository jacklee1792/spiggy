import sqlite3

from collections import defaultdict
from numpy import percentile
from typing import List, Tuple
from datetime import datetime
from pathlib import Path

from models.item import Item, GenericItem

BUFFER_MAX_LEN = 100
PERCENTILE = 20

_here = Path(__file__).parent
_conn = sqlite3.connect(_here/'database.db')
_ended_auctions_buffer = defaultdict(list)

_conn.execute(
    'CREATE TABLE IF NOT EXISTS price_history ('
    '  timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,'
    '  item_id         TEXT,'
    '  rarity          TEXT,'
    '  price           REAL'
    ')'
)


def _insert_to_buffer(item_id: str, rarity: str, price: float) -> None:
    """
    Insert a given (item_id, rarity, price) tuple into the buffer. Record a new
    price point in the database if the size of the buffer is no less than
    BUFFER_MAX_LEN after insertion.

    :param item_id: The item ID of the item to be recorded.
    :param rarity: The rariy of the item to be recorded.
    :param price: The price of the item to be recorded.
    :return: None.
    """
    buffer = _ended_auctions_buffer[(item_id, rarity)]
    buffer.append(price)
    if len(buffer) == BUFFER_MAX_LEN:
        sql = 'INSERT INTO price_history VALUES (CURRENT_TIMESTAMP, ?, ?, ?)'
        recorded_price = percentile(buffer, PERCENTILE)
        _conn.execute(sql, (item_id, rarity, recorded_price))
        print(f'OK Inserted item {(item_id, rarity)} at price {price}')
        buffer.clear()


def save_ended_auctions(items: List[Tuple[Item, float]]) -> None:
    """
    Given a list of items from recently ended auctions and their corresponding
    sale prices, save them into the database.

    Items which are instances of different Item subclasses have different
    methods of being stored in the database.

    :param items: A list of items and prices from recently ended auctions.
    :return: None.
    """
    for item, price in items:
        if isinstance(item, GenericItem):
            price_per_unit = price / item.stack_size
            _insert_to_buffer(item.item_id, item.rarity, price_per_unit)
        else:
            # Implement special pet handling later
            pass

    _conn.commit()


def get_historical_price(item_id: str, rarity: str) \
        -> List[Tuple[datetime, float]]:
    """
    For a given (item_id, rarity) pair, return the historical price of the item
    as a list of (datetime, price) pairs.

    :param item_id: The item ID of interest.
    :param rarity: The rarity of interest.
    :return: A list containing the historical price of the given parameters.
    """
    sql = 'SELECT timestamp, price FROM price_history WHERE ' \
          ' item_id = ? AND rarity = ?'
    results = _conn.execute(sql, (item_id, rarity)).fetchall()
    fun = lambda tp: (datetime.strptime(tp[0], '%Y-%m-%d %H:%M:%S'), tp[1])
    return list(map(fun, results))
