import functools
import sqlite3
from collections import defaultdict
from configparser import ConfigParser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

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


def db_write_guard(func: Callable) -> Callable:
    """
    Wrapper which ensures that the config allows writing to the database before
    writing to it.

    :param func:
    :return:
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if WRITE_TO_DATABASE:
            func(*args, **kwargs)
    return wrapper


@db_write_guard
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
    _conn.commit()


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
    counts = defaultdict(int)
    for rarity, occurrences in _conn.execute(sql, (item_id,)).fetchall():
        counts[rarity] += occurrences
    return max(counts, key=counts.get) if len(counts) else None
