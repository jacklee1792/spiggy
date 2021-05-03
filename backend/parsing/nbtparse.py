import base64
import io
import json
import re
from typing import List, Tuple, Optional, Any, Dict
from pathlib import Path

from nbt.nbt import NBTFile, TAG_Compound

_here = Path(__file__).parent

with open(_here/'exceptions/enchants.json') as f:
    ENCHANT_EXCEPTIONS = json.load(f)

with open(_here/'exceptions/reforges.json') as f:
    REFORGE_EXCEPTIONS = json.load(f)


def _without_nbt_style(s: str) -> str:
    """
    Given a full string with NBT styling, return the string without coloring
    and recomb symbols.

    :param s: The given string.
    :return: The given string without NBT styling.
    """
    return re.sub('§ka|§.', '', s).strip()


def deserialize(b64: str) -> NBTFile:
    """
    Decode the base-64 encoding of an item's metadata.

    :param b64: The raw base-64 representation of the item's metadata.
    :return: A NBTFile with the decoded metadata.
    """

    return NBTFile(fileobj=io.BytesIO(base64.b64decode(b64)))


def _get_extra_attrs(nbt: NBTFile) -> TAG_Compound:
    """
    Helper method to get the 'ExtraAttributes' tag compound from an item
    NBTFile. Useful for other extraction methods.

    :param nbt: The NBTFile to be read.
    :return: The 'ExtraAttributes' tag compound.
    """
    return nbt['i'][0]['tag']['ExtraAttributes']


def _get_pet_attrs(nbt: NBTFile) -> Dict[str, Any]:
    """
    Helper method to get the 'petInfo' tag and parse it into a dictionary.
    Returns an empty dictionary if no pet attributes are found.

    :param nbt: The NBTFile to be read.
    :return: Dictionary containing the pet attributes of the item.
    """
    extra_attrs = _get_extra_attrs(nbt)
    as_str = getattr(extra_attrs.get('petInfo'), 'value', '{}')
    return json.loads(as_str)


def extract_api_id(nbt: NBTFile) -> str:
    """
    Get the API ID of an item from its NBTFile.

    :param nbt: The NBTFile to be read.
    :return: The ID of the item, directly as it appears in the Skyblock API.
    """
    extra_attrs = _get_extra_attrs(nbt)
    return extra_attrs['id'].value


def extract_generic_base_name(nbt: NBTFile) -> str:
    """
    Given the NBTFile corresponding to an item, return its generic base name.

    This corresponds to removing special symbols and reforges from the raw
    display name. Often, dropping the first word is enough to remove the
    reforge, but some exceptions apply and are specified in REFORGE_EXCEPTIONS.

    :param nbt: The NBTFile to be read.
    :return: The name of the item with extra symbols removed and reforge
    dropped, if applicable.
    """
    name = re.sub('[✪⚚✦◆]', '', extract_generic_display_name(nbt)).strip()
    # No reforge, we are done
    if not extract_reforge(nbt):
        return name

    general_case = name.split(' ', 1)[-1]

    # If it's not an exception, just return the general case
    return REFORGE_EXCEPTIONS.get(name, general_case)


def extract_generic_display_name(nbt: NBTFile) -> str:
    """
    Extract the raw display name of an item (with NBT styling) from its NBTFile.

    :param nbt: The NBTFile to be read.
    :return: The api_name of the item, as a string.
    """
    return _without_nbt_style(nbt['i'][0]['tag']['display']['Name'].value)


def extract_identifiers(nbt: NBTFile) -> Tuple[str, str, str]:
    """
    Extract the item ID, base name, and display name of an items from its
    NBTFile.

    :param nbt: The NBTFile to be read.
    :return: A tuple describing the item ID, base name, and display name of the
    item.
    """
    api_id = extract_api_id(nbt)

    # Specialization for single-enchantment books
    if api_id == 'ENCHANTED_BOOK' and \
            len(enchants := extract_enchants(nbt)) == 1:
        enchant, lvl = enchants[0]
        # Replace enchant if it matches an exception
        enchant = ENCHANT_EXCEPTIONS.get(enchant, enchant)
        item_id = f'{enchant.upper()}_{lvl}_BOOK'
        base_name = item_id.title().replace('_', ' ')
        display_name = base_name

    # Specialization for runes
    elif api_id == 'RUNE':
        rune, lvl = extract_rune(nbt)
        item_id = f'{rune}_{lvl}_RUNE'
        base_name = extract_generic_base_name(nbt).rsplit(' ', 1)[0] \
            + f' {lvl}'
        display_name = extract_generic_display_name(nbt)

    # Specialization for pets
    elif api_id == 'PET':
        pet_type = extract_pet_type(nbt)
        item_id = f'{pet_type}_PET'
        base_name = item_id.title().replace('_', ' ')
        display_name = extract_generic_display_name(nbt)

    # General case
    else:
        # Drop the fragment prefix
        item_id = api_id.removeprefix('STARRED_')
        base_name = extract_generic_base_name(nbt)
        display_name = extract_generic_display_name(nbt)

    return item_id, base_name, display_name


def extract_stack_size(nbt: NBTFile) -> int:
    """
    Get the number of items in an item stack from the associated NBTFile.

    :param nbt: The NBTFile to be read.
    :return: The number of items in the item stack.
    """
    return nbt['i'][0]['Count'].value


def extract_rarity(nbt: NBTFile) -> str:
    """
    Get the rarity of an item from its NBTFile.

    :param nbt: The NBTFile to be read.
    :return: The rarity of the item.
    """
    last_lore_line = nbt['i'][0]['tag']['display']['Lore'][-1].value
    words = _without_nbt_style(last_lore_line).split()
    return words[0]


def extract_rune(nbt: NBTFile) -> Optional[Tuple[str, int]]:
    """
    Get rune information of an item from its NBTFile.

    :param nbt: The NBTFile to be read.
    :return: The rune of the item as a (rune name, level) pair, or None if no
    rune is associated with the item.
    """
    extra_attrs = _get_extra_attrs(nbt)
    if 'runes' in extra_attrs:
        items = list(extra_attrs['runes'].items())
        return items[0][0], items[0][1].value
    return None


def extract_enchants(nbt: NBTFile) -> List[Tuple[str, int]]:
    """
    Get enchantment information of an item from its NBTFile.

    :param nbt: The NBTFile to be read.
    :return: A list of (enchantment, level) pairs describing the enchantments
    on the item
    """
    extra_attrs = _get_extra_attrs(nbt)
    enchantments = extra_attrs.get('enchantments', {}).items()
    return [(ench, lvl.value) for ench, lvl in enchantments]


def extract_is_recombobulated(nbt: NBTFile) -> bool:
    """
    Determine whether or not an item is recombobulated from its NBTFile.

    :param nbt: The NBTFile to be read.
    :return: Boolean, whether or not the item is recombobulated.
    """
    extra_attrs = _get_extra_attrs(nbt)
    return 'rarity_upgrades' in extra_attrs


def extract_is_fragged(nbt: NBTFile) -> bool:
    """
    Determine whether or not an item has a Bonzo or Livid fragment applied to
    it from its NBTFile.

    :param nbt: The NBTFile to be read.
    :return: Boolean, whether or not the item is fragged.
    """
    return extract_api_id(nbt).startswith('STARRED_')


def extract_hot_potato_count(nbt: NBTFile) -> int:
    """
    Determine the number of hot potato book upgrades on an item from its
    NBTFile.

    :param nbt: The NBTFile to be read.
    :return: The number of hot potato book upgrades on the given item.
    """
    extra_attrs = _get_extra_attrs(nbt)
    return getattr(extra_attrs.get('hot_potato_count'), 'value', 0)


def extract_reforge(nbt: NBTFile) -> Optional[str]:
    """
    Get the reforge on an item from its NBTFile.

    :param nbt: The NBTFile to be read.
    :return: The reforge of the item, or None if no reforge is present.
    """
    extra_attrs = _get_extra_attrs(nbt)
    return getattr(extra_attrs.get('modifier'), 'value', None)


def extract_dungeon_stars(nbt: NBTFile) -> int:
    """
    Get the number of dungeon stars on an item from its NBTFile.

    :param nbt: The NBTFile to be read.
    :return: The number of dungeon stars on the item.
    """
    extra_attrs = _get_extra_attrs(nbt)
    return getattr(extra_attrs.get('dungeon_item_level'), 'value', 0)


def extract_pet_type(nbt: NBTFile) -> Optional[str]:
    """
    Get the pet type of an item from its NBTFile.

    :param nbt: The NBTFile to be read.
    :return: The pet type of the item, if applicable.
    """
    pet_attrs = _get_pet_attrs(nbt)
    return pet_attrs.get('type')


def extract_pet_exp(nbt: NBTFile) -> float:
    """
    Get the pet experience of an item from its NBTFile.

    :param nbt: The NBTFile to be read.
    :return: The pet experience on the item.
    """
    pet_attrs = _get_pet_attrs(nbt)
    return pet_attrs.get('exp', 0)


def extract_pet_candy_used(nbt: NBTFile) -> int:
    """
    Get the number of pet candies used on an item from its NBTFile.

    :param nbt: The NBTFile to be read.
    :return: The number of pet candies on the item.
    """
    pet_attrs = _get_pet_attrs(nbt)
    return pet_attrs.get('candyUsed', 0)


if __name__ == '__main__':

    # Some tools for testing and debugging

    def summarize(b64: str, verbose: bool = True) -> None:
        item_nbt = deserialize(b64)

        api_id = extract_api_id(item_nbt)
        generic_display_name = extract_generic_display_name(item_nbt)
        stack_size = extract_stack_size(item_nbt)
        rarity = extract_rarity(item_nbt)
        rune = extract_rune(item_nbt)
        enchants = extract_enchants(item_nbt)
        is_recombobulated = extract_is_recombobulated(item_nbt)
        is_fragged = extract_is_fragged(item_nbt)
        hot_potato_count = extract_hot_potato_count(item_nbt)
        reforge = extract_reforge(item_nbt)
        dungeon_stars = extract_dungeon_stars(item_nbt)
        pet_type = extract_pet_type(item_nbt)
        pet_exp = extract_pet_exp(item_nbt)
        pet_candy_used = extract_pet_candy_used(item_nbt)
        identifiers = extract_identifiers(item_nbt)

        if verbose:
            print(b64)
            print(item_nbt.pretty_tree())

        print('api_id:              ', api_id)
        print('generic_display_name:', generic_display_name)
        print('stack_size:          ', stack_size)
        print('rarity:              ', rarity)
        print('rune:                ', rune)
        print('enchants:            ', enchants[:5])
        print('is_recombobulated:   ', is_recombobulated)
        print('is_fragged:          ', is_fragged)
        print('hot_potato_count:    ', hot_potato_count)
        print('reforge:             ', reforge)
        print('dungeon_stars:       ', dungeon_stars)
        print('pet_type:            ', pet_type)
        print('pet_exp:             ', pet_exp)
        print('pet_candy_used:      ', pet_candy_used)
        print('identifier item_id:  ', identifiers[0])
        print('identifier base_name:', identifiers[1])
        print('identifier full_name:', identifiers[2])
        print()

    mode = input('Enter "manual" for manual mode, or anything else to run '
                 'testing on all recently ended auctions: ')
    if mode == 'manual':
        inp = input('Enter item NBT as b64 string:')
        summarize(inp)
    else:
        import requests
        res = requests.get('https://api.hypixel.net/skyblock/auctions_ended')
        for auction in res.json()['auctions']:
            b64 = auction['item_bytes']
            summarize(b64, verbose=False)
