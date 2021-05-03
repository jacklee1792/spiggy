import json
import re

from typing import Tuple, Optional





def get_book_id_basename(hy_enchant: str, lvl: int) -> Tuple[str, str]:
    """
    Given the Skyblock API name of a single enchantment with its level, return a
    (item_id, basename) pair for a book with that single enchantment.

    :param hy_enchant: The Skyblock API's code for the enchantment.
    :param lvl: The level of the enchantment.
    :return: Pair of strings, representing the corresponding (item_id, basename)
    pair.

    >>> get_book_id_basename('ultimate_soul_eater', 5)
    ('SOUL_EATER_5_BOOK', 'Soul Eater V Book')
    """

    # Strip the "ultimate" word first
    dont_strip = {"ultimate_wise", "ultimate_jerry"}
    if hy_enchant.startswith('ultimate') and hy_enchant not in dont_strip:
        hy_enchant = hy_enchant[9:]

    item_id = f'{hy_enchant.upper()}_{lvl}_BOOK'
    basename = f'{hy_enchant.replace("_", " ").title()} {to_roman(lvl)} Book'
    return item_id, basename
