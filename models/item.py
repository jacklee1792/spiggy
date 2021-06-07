import logging
from typing import List, Optional, Tuple

from backend.parsing import nbtparse


class Item:
    """
    Class defining a Skyblock item.
    """
    item_id: str
    base_name: str
    display_name: str
    stack_size: int
    rarity: str

    rune: Optional[Tuple[str, int]]
    enchants: List[Tuple[str, int]]
    is_recombobulated: bool
    is_fragged: bool
    hot_potato_count: int
    reforge: Optional[str]
    dungeon_stars: int

    def __init__(self, b64: str) -> None:
        """
        Construct a GenericItem instance from its base64 NBT Representation.

        :return: None.
        """
        nbt = nbtparse.deserialize(b64)

        self.item_id, self.base_name, self.display_name = \
            nbtparse.extract_identifiers(nbt)
        self.stack_size = nbtparse.extract_stack_size(nbt)
        self.rarity = nbtparse.extract_rarity(nbt)

        self.rune = nbtparse.extract_rune(nbt)
        self.enchants = nbtparse.extract_enchants(nbt)
        self.is_recombobulated = nbtparse.extract_is_recombobulated(nbt)
        self.is_fragged = nbtparse.extract_is_fragged(nbt)
        self.hot_potato_count = nbtparse.extract_hot_potato_count(nbt)
        self.reforge = nbtparse.extract_reforge(nbt)
        self.dungeon_stars = nbtparse.extract_dungeon_stars(nbt)

    def has_ascii_base_name(self) -> bool:
        """
        Determine whether or not the base name consists solely of ASCII
        characters, and log if it doesn't

        :return: Whether or not the base name consists solely of ASCII
        characters
        """
        ok = all(ord(c) < 128 for c in self.base_name)
        if not ok:
            logging.info(f'Found item with non-ASCII base name '
                         f'{self.base_name}')
        return ok
