import functools
import sqlite3
from collections import defaultdict
from configparser import ConfigParser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

from fuzzywuzzy import fuzz, process

from backend import constants
from models.item import Item


_here = Path(__file__).parent
_cfg = ConfigParser()
_cfg.read(_here.parent.parent / 'config/spiggy.ini')

WRITE_TO_DATABASE = _cfg['Database'].getboolean('WriteToDatabase')

_conn = sqlite3.connect(_here/'database.db')
_conn.execute(
    'CREATE TABLE IF NOT EXISTS price_history ('
    '  timestamp      DATETIME DEFAULT CURRENT_TIMESTAMP,'
    '  item_id        TEXT,'
    '  rarity         TEXT,'
    '  price          REAL,'
    '  occurrences    INTEGER'
    ')'
)

_conn.execute(
    'CREATE TABLE IF NOT EXISTS name_link ('
    '  item_id        TEXT,'
    '  basename       TEXT'
    ')'
)

_conn.execute(
    'CREATE UNIQUE INDEX IF NOT EXISTS name_idx '
    'ON name_link(item_id, base_name)'
)


def db_write(func: Callable) -> Callable:
    """
    Wrapper which ensures that the config allows writing to the database before
    writing to it, and commits after the operation.

    :param func:
    :return:
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if WRITE_TO_DATABASE:
            func(*args, **kwargs)
            _conn.commit()
    return wrapper


@db_write
def save_prices(d: Dict[Tuple[str, str], Tuple[float, int]]) -> None:
    """
    Given a dict which maps a (item_id, rarity) pairs to (price, occurrences)
    pairs, record it in the database.

    :param d: The calculated prices to be stored.
    :return: None.
    """
    sql = 'INSERT INTO price_history VALUES (CURRENT_TIMESTAMP, ?, ?, ?, ?)'
    for (item_id, rarity), (price, occurrences) in d.items():
        _conn.execute(sql, (item_id, rarity, price, occurrences))


def get_historical_price(item_id: str, rarity: str, days: int) \
        -> List[Tuple[datetime, float]]:
    """
    For a given (item_id, rarity) pair, return the historical price of the item
    as a list of (datetime, price) pairs.
    :param item_id: The item ID of interest.
    :param rarity: The rarity of interest.
    :param days: The number of days worth of data to retrieve.
    :return: A list containing the historical price of the given parameters.
    """

    # Add date parameter later
    sql = 'SELECT timestamp, price FROM price_history WHERE' \
          ' item_id = ? AND rarity = ? AND timestamp > ?'
    date_constraint = datetime.now() - timedelta(days=days)
    results = _conn.execute(sql, (item_id, rarity, date_constraint)).fetchall()

    def as_datetime(s: str) -> datetime:
        return datetime.strptime(s, '%Y-%m-%d %H:%M:%S')
    return [(as_datetime(dt), price) for dt, price in results]


def guess_rarity(item_id: str) -> Optional[str]:
    """
    Find the most predominant rarity for a given item_id if it exists in the
    database.

    :param item_id: The item id to be checked.
    :return: The most predominant rarity of the given item_id, if it exists.
    """
    sql = 'SELECT rarity, occurrences FROM price_history WHERE item_id = ?'
    results = _conn.execute(sql, (item_id,)).fetchall()
    # Take the most common rarity for pets
    if item_id.endswith('_PET'):
        counts = defaultdict(int)
        for rarity, occurrences in results:
            counts[rarity] += occurrences
        return max(counts, key=counts.get) if len(counts) else None
    # Take the lowest rarity for other items
    else:
        rarities = [result[0] for result in results]

        def rarity_index(r):
            return list(constants.RARITIES.keys()).index(r)
        print(min(rarities, key=rarity_index))
        return min(rarities, key=rarity_index)


@db_write
def save_name_links(items: List[Item]) -> None:
    """
    Given a list of items, take into account their item ID/base name
    relationships and record them into database.

    :param items: The items to be recorded into the database.
    :return: None.
    """
    sql = 'INSERT OR REPLACE INTO name_link VALUES (?, ?)'
    for item in items:
        _conn.execute(sql, (item.item_id, item.base_name))


def guess_item_id(base_name: str) -> str:
    """
    Find the base name recorded in the database which is the most similar to
    the given base name.

    :param base_name: The base name to be matched.
    :return: The best item ID match for the given base name.
    """
    sql = 'SELECT base_name FROM name_link'
    choices = _conn.execute(sql).fetchall()
    base_name_match = process.extractOne(base_name, choices)[0][0]
    sql2 = 'SELECT item_id FROM name_link WHERE base_name = ?'
    return _conn.execute(sql2, (base_name_match,)).fetchone()[0]
