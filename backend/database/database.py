import functools
import sqlite3
import statistics
from configparser import ConfigParser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Callable

from fuzzywuzzy import process

from backend import constants
from models.auction import ActiveAuction


_here = Path(__file__).parent
_cfg = ConfigParser()
_cfg.read(_here.parent.parent / 'config/spiggy.ini')


_conn = sqlite3.connect(_here/'database.db',
                        detect_types=sqlite3.PARSE_DECLTYPES)


WRITE_TO_DATABASE = _cfg['Database'].getboolean('WriteToDatabase')


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


# Table which tracks the lowest BIN history of a (item ID, rarity) pair
_conn.execute(
    'CREATE TABLE IF NOT EXISTS lbin_history ('
    '  timestamp      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,'
    '  item_id        TEXT,'
    '  rarity         TEXT,'
    '  price          REAL'
    ')'
)
_conn.execute(
    'CREATE INDEX IF NOT EXISTS lbin_history_idx '
    'ON lbin_history(item_id, rarity)'
)


@db_write
def save_lbin_history(buffer: Dict[Tuple[str, str], List[float]]) -> None:
    """
    Given a dict which maps (item_id, rarity) pairs to prices, record it in the
    database.

    :param buffer: The lowest BIN buffer to be recorded.
    :return: None.
    """
    sql = 'INSERT INTO lbin_history VALUES (?, ?, ?, ?)'
    now = datetime.now()
    for (item_id, rarity), prices in buffer.items():
        _conn.execute(sql, (now, item_id, rarity, statistics.mean(prices)))


def get_lbin_history(item_id: str, rarity: str,
                     span: timedelta) -> List[Tuple[datetime, float]]:
    """
    Get lowest BIN records from the database which have the given item ID and
    rarity pair.

    :param item_id: The item ID to get records for.
    :param rarity: The rarity of the item to get records for.
    :param span: The timespan of the data to be returned.
    :return: None.
    """
    sql = 'SELECT timestamp, price FROM lbin_history ' \
          'WHERE item_id = ? AND rarity = ? AND timestamp >= ?'
    min_time = datetime.now() - span
    return _conn.execute(sql, (item_id, rarity, min_time)).fetchall()


# Table which tracks the average sale history of a (item ID, rarity) pair
_conn.execute(
    'CREATE TABLE IF NOT EXISTS avg_sale_history ('
    '  timestamp      DATETIME DEFAULT CURRENT_TIMESTAMP,'
    '  item_id        TEXT,'
    '  rarity         TEXT,'
    '  price          REAL'
    ')'
)
_conn.execute(
    'CREATE INDEX IF NOT EXISTS avg_sale_history_idx '
    'ON avg_sale_history(item_id, rarity)'
)


@db_write
def save_avg_sale_history(buffer: Dict[Tuple[str, str], List[float]]) -> None:
    """
    Given a dict which maps (item_id, rarity) pairs to prices, record it in
    the database.

    :param buffer: The average sale buffer to be recorded.
    :return: None.
    """
    sql = 'INSERT INTO avg_sale_history VALUES (?, ?, ?, ?)'
    now = datetime.now()
    for (item_id, rarity), prices in buffer.items():
        _conn.execute(sql, (now, item_id, rarity, statistics.mean(prices)))


def get_avg_sale_history(item_id: str, rarity: str,
                         span: timedelta) -> List[Tuple[datetime, float]]:
    """
    Get average sale records from the database which have the given item ID and
    rarity pair.

    :param item_id: The item ID to get records for.
    :param rarity: The rarity of the item to get records for.
    :param span: The timespan of the data to be returned.
    :return: None.
    """
    sql = 'SELECT timestamp, price FROM lbin_history ' \
          'WHERE item_id = ? AND rarity = ? AND timestamp >= ?'
    min_time = datetime.now() - span
    return _conn.execute(sql, (item_id, rarity, min_time)).fetchall()


# Table which tracks bazaar price history
_conn.execute(
    'CREATE TABLE IF NOT EXISTS bazaar_history ('
    '  timestamp      DATETIME DEFAULT CURRENT_TIMESTAMP,'
    '  item_id        TEXT,'
    '  buy_price      REAL,'
    '  sell_price     REAL,'
    '  buy_volume     REAL,'
    '  sell_volume    REAL'
    ')'
)
_conn.execute(
    'CREATE INDEX IF NOT EXISTS bazaar_history_idx '
    'ON bazaar_history(item_id)'
)

# Table which maps item IDs to base names and occurrences in different rarities
_conn.execute(
    'CREATE TABLE IF NOT EXISTS item_info ('
    '  item_id        TEXT UNIQUE,'
    '  base_name      TEXT,'
    '  common_ct      INTEGER DEFAULT 0,'
    '  uncommon_ct    INTEGER DEFAULT 0,'
    '  rare_ct        INTEGER DEFAULT 0,'
    '  epic_ct        INTEGER DEFAULT 0,'
    '  legendary_ct   INTEGER DEFAULT 0,'
    '  mythic_ct      INTEGER DEFAULT 0,'
    '  supreme_ct     INTEGER DEFAULT 0,'
    '  special_ct     INTEGER DEFAULT 0,'
    '  v_special_ct   INTEGER DEFAULT 0,'
    '  unknown_ct     INTEGER DEFAULT 0'
    ')'
)


@db_write
def save_item_info(active_auctions: List[ActiveAuction],
                   **kwargs) -> None:
    """
    Given a list of the active auctions, update the item ID -> base name and
    rarity count mapping.

    :param active_auctions: The list of active auctions to consider.
    :return: None.
    """
    sql = 'INSERT INTO item_info (item_id, base_name) VALUES (?, ?) ' \
          'ON CONFLICT (item_id) DO UPDATE SET base_name = ?'
    col_names = {
        'COMMON': 'common_ct',
        'UNCOMMON': 'uncommon_ct',
        'RARE': 'rare_ct',
        'EPIC': 'epic_ct',
        'LEGENDARY': 'legendary_ct',
        'MYTHIC': 'mythic_ct',
        'SUPREME': 'supreme_ct',
        'SPECIAL': 'special_ct',
        'VERY_SPECIAL': 'v_special_ct',
        'UNKNOWN': 'unknown_ct'
    }

    for auction in active_auctions:
        item_id = auction.item.item_id
        base_name = auction.item.base_name
        rarity = auction.item.rarity
        # Create new row or update the base name for an existing row
        _conn.execute(sql, (item_id, base_name, base_name))
        # Update the count
        col_name = col_names[rarity]
        _conn.execute(f'UPDATE item_info SET {col_name} = {col_name} + 1 '
                      f'WHERE item_id = ?', (item_id,))


def guess_rarity(item_id: str) -> Optional[str]:
    """
    Guess the rarity of an item from its item ID. For most items, take the
    lowest rarity which has appeared in active auctions. For pets, take the
    rarity which occurs the most.

    :param item_id: The item ID to guess with.
    :return: The guess of the rarity.
    """
    sql = 'SELECT * FROM item_info WHERE item_id = ?'
    rarities = constants.RARITIES.keys()
    counts = _conn.execute(sql, (item_id,)).fetchone()[2:12]

    if item_id.endswith('_PET'):
        return max(zip(rarities, counts), key=lambda tp: tp[1])[0]
    else:
        non_zero_rarities = [(r, c) for r, c in zip(rarities, counts) if c > 0]
        return non_zero_rarities[0][0]


def guess_identifiers(fuzzy_base_name: str) -> Tuple[str, str]:
    """
    Given a fuzzy base name, guess the corresponding (item ID, base name)
    identifier pair.

    :param fuzzy_base_name: The base name to be matched.
    :return: The identifier pair with the closest matching base name.
    """
    sql = 'SELECT base_name FROM item_info'
    choices = _conn.execute(sql).fetchall()
    base_name = process.extractOne(fuzzy_base_name, choices)[0][0]
    sql2 = 'SELECT item_id FROM item_info WHERE base_name = ?'
    item_id = _conn.execute(sql2, (base_name,)).fetchone()[0]
    return item_id, base_name
