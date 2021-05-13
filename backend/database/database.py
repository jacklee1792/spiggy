import sqlite3

from typing import List
from pathlib import Path

from datetime import datetime
from typing import Tuple, Dict
from models.auction import ActiveAuction


_here = Path(__file__).parent
_conn = sqlite3.connect(_here/'database.db')

_conn.execute(
    'CREATE TABLE IF NOT EXISTS price_history ('
    '  timestamp       DATETIME DEFAULT CURRENT_TIMESTAMP,'
    '  item_id         TEXT,'
    '  rarity          TEXT,'
    '  price           REAL'
    ')'
)


def save_prices(d: Dict[Tuple[str, str], float]) -> None:
    """
    Given a dict which maps a (item_id, rarity) pairs to prices, record it in
    the database.

    :param d: The calculated prices to be stored.
    :return: None.
    """
    sql = 'INSERT INTO price_history VALUES (CURRENT_TIMESTAMP, ?, ?, ?)'
    for (item_id, rarity), price in d.items():
        _conn.execute(sql, (item_id, rarity, price))
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

    def as_datetime(s: str) -> datetime:
        return datetime.strptime(s, '%Y-%m-%d %H:%M:%S')

    return [(as_datetime(dt), price) for dt, price in results]
