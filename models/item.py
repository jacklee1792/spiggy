from typing import List, Optional, Tuple

from backend.parsing import nbtparse


class Item:
    """
    Abstract class which defines a Skyblock item.
    """
    item_id: str
    base_name: str
    display_name: str
    stack_size: int
    rarity: str


class GenericItem(Item):
    """
    Class defining generic items which don't have to be handled separately in
    the database (eg. swords, armor, blocks).
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


def make_item(b64: str) -> Item:
    """
    Factory function which produces the correct subclass of Item from the
    "item_bytes" field as it appears in the Skyblock API.

    :param b64: The base-64 representation of the item bytes.
    :return: A corresponding Item subclass instance.
    """

    # For now, just treat everything as a GenericItem
    return GenericItem(b64)
