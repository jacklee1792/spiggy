import base64
import gzip
import io
import json
import re
import struct
from pathlib import Path
from typing import Any, BinaryIO, Dict, List, Optional, Tuple, Union

from backend import constants

_here = Path(__file__).parent

with open(_here/'exceptions/enchants.json') as f:
    ENCHANT_EXCEPTIONS = json.load(f)

with open(_here/'exceptions/reforges.json') as f:
    REFORGE_EXCEPTIONS = json.load(f)


def _pop_byte(bytes_f: BinaryIO) -> int:
    return int.from_bytes(bytes_f.read(1),
                          byteorder='big', signed=True)


def _pop_ushort(bytes_f: BinaryIO) -> int:
    return int.from_bytes(bytes_f.read(2),
                          byteorder='big', signed=False)


def _pop_short(bytes_f: BinaryIO) -> int:
    return int.from_bytes(bytes_f.read(2),
                          byteorder='big', signed=True)


def _pop_int(bytes_f: BinaryIO) -> int:
    return int.from_bytes(bytes_f.read(4),
                          byteorder='big', signed=True)


def _pop_long(bytes_f: BinaryIO) -> int:
    return int.from_bytes(bytes_f.read(8),
                          byteorder='big', signed=True)


def _pop_string(bytes_f: BinaryIO) -> str:
    payload = _pop_ushort(bytes_f)
    return bytes_f.read(payload).decode('utf-8')


class NbtTag:
    """
    Class defining an NbtTag: a value with an intrinsic name.
    """
    name: str
    value: Any

    def __init__(self, name: str, value: Any):
        """
        Construct an NbtTag instance.

        :param name: The name of the NbtTag.
        :param value: The value of the NbtTag.
        """
        self.name = name
        self.value = value

    def __getitem__(self, key: Union[str, int]):
        """
        Call __getitem__ on the NbtTag's value instance variable.

        :param key: The desired key.
        :return: The value of the key in the value instance variable.
        """
        return self.value[key]


def parse_byte(bytes_f: BinaryIO, read_name: bool = True) -> NbtTag:
    name = _pop_string(bytes_f) if read_name else ''
    return NbtTag(name, _pop_byte(bytes_f))


def parse_short(bytes_f: BinaryIO, read_name: bool = True) -> NbtTag:
    name = _pop_string(bytes_f) if read_name else ''
    return NbtTag(name, _pop_short(bytes_f))


def parse_int(bytes_f: BinaryIO, read_name: bool = True) -> NbtTag:
    name = _pop_string(bytes_f) if read_name else ''
    return NbtTag(name, _pop_int(bytes_f))


def parse_long(bytes_f: BinaryIO, read_name: bool = True) -> NbtTag:
    name = _pop_string(bytes_f) if read_name else ''
    return NbtTag(name, _pop_long(bytes_f))


def parse_float(bytes_f: BinaryIO, read_name: bool = True) -> NbtTag:
    name = _pop_string(bytes_f) if read_name else ''
    return NbtTag(name, struct.unpack('>f', bytes_f.read(4)))


def parse_double(bytes_f: BinaryIO, read_name: bool = True) -> NbtTag:
    name = _pop_string(bytes_f) if read_name else ''
    return NbtTag(name, struct.unpack('>d', bytes_f.read(8)))


def parse_byte_array(bytes_f: BinaryIO, read_name: bool = True) -> NbtTag:
    name = _pop_string(bytes_f) if read_name else ''
    payload = _pop_int(bytes_f)
    arr = [_pop_byte(bytes_f) for _ in range(payload)]
    return NbtTag(name, arr)


def parse_string(bytes_f: BinaryIO, read_name: bool = True) -> NbtTag:
    name = _pop_string(bytes_f) if read_name else ''
    return NbtTag(name, _pop_string(bytes_f))


def parse_list(bytes_f: BinaryIO, read_name: bool = True) -> NbtTag:
    name = _pop_string(bytes_f) if read_name else ''
    content_type = _pop_byte(bytes_f)
    payload = _pop_int(bytes_f)
    ret = []
    for _ in range(payload):
        ret.append(PARSERS[content_type](bytes_f, read_name=False))
    return NbtTag(name, ret)


def parse_compound(bytes_f: BinaryIO, read_name: bool = True) -> NbtTag:
    name = _pop_string(bytes_f) if read_name else ''
    tag_type = _pop_byte(bytes_f)
    ret = {}
    while tag_type != 0:
        tag = PARSERS[tag_type](bytes_f)
        ret[tag.name] = tag.value
        tag_type = _pop_byte(bytes_f)
    return NbtTag(name, ret)


def parse_int_array(bytes_f: BinaryIO, read_name: bool = True) -> NbtTag:
    name = _pop_string(bytes_f) if read_name else ''
    payload = _pop_int(bytes_f)
    arr = [_pop_int(bytes_f) for _ in range(payload)]
    return NbtTag(name, arr)


def parse_long_array(bytes_f: BinaryIO, read_name: bool = True) -> NbtTag:
    name = _pop_string(bytes_f) if read_name else ''
    payload = _pop_int(bytes_f)
    arr = [_pop_long(bytes_f) for _ in range(payload)]
    return NbtTag(name, arr)


PARSERS = [
    None,
    parse_byte,
    parse_short,
    parse_int,
    parse_long,
    parse_float,
    parse_double,
    parse_byte_array,
    parse_string,
    parse_list,
    parse_compound,
    parse_int_array,
    parse_long_array
]


def _without_nbt_style(s: str) -> str:
    """
    Given a full string with NBT styling, return the string without coloring
    and recomb symbols.

    :param s: The given string.
    :return: The given string without NBT styling.
    """
    return re.sub('§ka|§.', '', s).strip()


def deserialize(b64: str) -> NbtTag:
    """
    Decode the gzipped base-64 encoding of an item's metadata.

    :param b64: The gzipped base-64 item metadata.
    :return: A NbtTag with the decoded metadata.
    """
    bytes_gz = base64.b64decode(b64)
    bytes_f = io.BytesIO(gzip.decompress(bytes_gz))

    # Pop the outer compound tag indicator
    _pop_byte(bytes_f)
    return parse_compound(bytes_f)


def _get_extra_attrs(nbt: NbtTag) -> Dict[str, Any]:
    """
    Helper method to get the 'ExtraAttributes' tag compound from an item
    NbtTag. Useful for other extraction methods.

    :param nbt: The NbtTag to be read.
    :return: The 'ExtraAttributes' tag compound.
    """
    return nbt['i'][0]['tag']['ExtraAttributes']


def _get_pet_attrs(nbt: NbtTag) -> Dict[str, Any]:
    """
    Helper method to get the 'petInfo' tag and parse it into a dictionary.
    Returns an empty dictionary if no pet attributes are found.

    :param nbt: The NbtTag to be read.
    :return: Dictionary containing the pet attributes of the item.
    """
    extra_attrs = _get_extra_attrs(nbt)
    as_str = extra_attrs.get('petInfo', '{}')
    return json.loads(as_str)


def extract_api_id(nbt: NbtTag) -> str:
    """
    Get the API ID of an item from its NbtTag.

    :param nbt: The NbtTag to be read.
    :return: The ID of the item, directly as it appears in the Skyblock API.
    """
    extra_attrs = _get_extra_attrs(nbt)
    return extra_attrs['id']


def extract_generic_base_name(nbt: NbtTag) -> str:
    """
    Given the NbtTag corresponding to an item, return its generic base name.

    This corresponds to removing special symbols and reforges from the raw
    display name. Often, dropping the first word is enough to remove the
    reforge, but some exceptions apply and are specified in REFORGE_EXCEPTIONS.

    :param nbt: The NbtTag to be read.
    :return: The name of the item with extra symbols removed and reforge
    dropped, if applicable.
    """
    name = re.sub('[✪⚚✦◆™©�]', '', extract_generic_display_name(nbt)).strip()
    # No reforge, we are done
    if not extract_reforge(nbt):
        return name

    general_case = name.split(' ', 1)[-1]

    # If it's not an exception, just return the general case
    return REFORGE_EXCEPTIONS.get(name, general_case)


def extract_generic_display_name(nbt: NbtTag) -> str:
    """
    Extract the raw display name of an item (with NBT styling) from its NbtTag.

    :param nbt: The NbtTag to be read.
    :return: The api_name of the item, as a string.
    """
    return _without_nbt_style(nbt['i'][0]['tag']['display']['Name'])


def extract_identifiers(nbt: NbtTag) -> Tuple[str, str, str]:
    """
    Extract the item ID, base name, and display name of an items from its
    NbtTag.

    :param nbt: The NbtTag to be read.
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
        item_id = f'{rune}_RUNE_{lvl}'
        base_name = extract_generic_base_name(nbt).rsplit(' ', 1)[0] \
            + f' {lvl}'
        display_name = extract_generic_display_name(nbt)

    # Specialization for pets
    elif api_id == 'PET':
        pet_type = extract_pet_type(nbt)
        item_id = f'{pet_type}_PET'
        base_name = item_id.title().replace('_', ' ')
        display_name = extract_generic_display_name(nbt)

    # Specialization for cake souls
    elif api_id == 'CAKE_SOUL':
        item_id = 'CAKE_SOUL'
        base_name = 'Cake Soul'
        display_name = extract_generic_display_name(nbt)

    # General case
    else:
        # Drop the fragment prefix
        item_id = api_id.removeprefix('STARRED_')
        base_name = extract_generic_base_name(nbt)
        display_name = extract_generic_display_name(nbt)

    return item_id, base_name, display_name


def extract_stack_size(nbt: NbtTag) -> int:
    """
    Get the number of items in an item stack from the associated NbtTag.

    :param nbt: The NbtTag to be read.
    :return: The number of items in the item stack.
    """
    return nbt['i'][0]['Count']


def extract_rarity(nbt: NbtTag) -> str:
    """
    Get the rarity of an item from its NbtTag.

    :param nbt: The NbtTag to be read.
    :return: The rarity of the item.
    """
    try:
        lore = nbt['i'][0]['tag']['display']['Lore']
        rarity_line = nbt['i'][0]['tag']['display']['Lore'][-1].value

        # Some runes have a weird footer in their lore
        if extract_api_id(nbt) == 'RUNE':
            for tag in lore:
                line = tag.value
                if _without_nbt_style(line).endswith('COSMETIC'):
                    rarity_line = line

        words = _without_nbt_style(rarity_line).split()
        # Account for 'VERY_SPECIAL' case
        rarity = words[0] if words[0] != 'VERY' else 'VERY_SPECIAL'
        return rarity if rarity in constants.RARITIES.keys() else 'UNKNOWN'
    except KeyError:
        # Some weird items don't have lore for some reason
        return 'UNKNOWN'


def extract_rune(nbt: NbtTag) -> Optional[Tuple[str, int]]:
    """
    Get rune information of an item from its NbtTag.

    :param nbt: The NbtTag to be read.
    :return: The rune of the item as a (rune name, level) pair, or None if no
    rune is associated with the item.
    """
    extra_attrs = _get_extra_attrs(nbt)
    if 'runes' in extra_attrs:
        return list(extra_attrs['runes'].items())[0]
    return None


def extract_enchants(nbt: NbtTag) -> List[Tuple[str, int]]:
    """
    Get enchantment information of an item from its NbtTag.

    :param nbt: The NbtTag to be read.
    :return: A list of (enchantment, level) pairs describing the enchantments
    on the item
    """
    extra_attrs = _get_extra_attrs(nbt)
    enchantments = extra_attrs.get('enchantments', {}).items()
    return [(ench, lvl) for ench, lvl in enchantments]


def extract_is_recombobulated(nbt: NbtTag) -> bool:
    """
    Determine whether or not an item is recombobulated from its NbtTag.

    :param nbt: The NbtTag to be read.
    :return: Boolean, whether or not the item is recombobulated.
    """
    extra_attrs = _get_extra_attrs(nbt)
    return 'rarity_upgrades' in extra_attrs


def extract_is_fragged(nbt: NbtTag) -> bool:
    """
    Determine whether or not an item has a Bonzo or Livid fragment applied to
    it from its NbtTag.

    :param nbt: The NbtTag to be read.
    :return: Boolean, whether or not the item is fragged.
    """
    return extract_api_id(nbt).startswith('STARRED_')


def extract_hot_potato_count(nbt: NbtTag) -> int:
    """
    Determine the number of hot potato book upgrades on an item from its
    NbtTag.

    :param nbt: The NbtTag to be read.
    :return: The number of hot potato book upgrades on the given item.
    """
    extra_attrs = _get_extra_attrs(nbt)
    return extra_attrs.get('hot_potato_count', 0)


def extract_reforge(nbt: NbtTag) -> Optional[str]:
    """
    Get the reforge on an item from its NbtTag.

    :param nbt: The NbtTag to be read.
    :return: The reforge of the item, or None if no reforge is present.
    """
    extra_attrs = _get_extra_attrs(nbt)
    return extra_attrs.get('modifier')


def extract_dungeon_stars(nbt: NbtTag) -> int:
    """
    Get the number of dungeon stars on an item from its NbtTag.

    :param nbt: The NbtTag to be read.
    :return: The number of dungeon stars on the item.
    """
    extra_attrs = _get_extra_attrs(nbt)
    return extra_attrs.get('dungeon_item_level', 0)


def extract_pet_type(nbt: NbtTag) -> Optional[str]:
    """
    Get the pet type of an item from its NbtTag.

    :param nbt: The NbtTag to be read.
    :return: The pet type of the item, if applicable.
    """
    pet_attrs = _get_pet_attrs(nbt)
    return pet_attrs.get('type')


def extract_pet_exp(nbt: NbtTag) -> float:
    """
    Get the pet experience of an item from its NbtTag.

    :param nbt: The NbtTag to be read.
    :return: The pet experience on the item.
    """
    pet_attrs = _get_pet_attrs(nbt)
    return pet_attrs.get('exp', 0)


def extract_pet_candy_used(nbt: NbtTag) -> int:
    """
    Get the number of pet candies used on an item from its NbtTag.

    :param nbt: The NbtTag to be read.
    :return: The number of pet candies on the item.
    """
    pet_attrs = _get_pet_attrs(nbt)
    return pet_attrs.get('candyUsed', 0)
