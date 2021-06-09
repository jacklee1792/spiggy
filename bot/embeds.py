import statistics
from datetime import datetime, timedelta
from typing import List, Tuple

from discord import Embed

from backend import constants
from backend.database import database
from bot import utils

FAIL_COLOUR = 0xC10016
OK_COLOUR = 0x0198E1

NO_PERMISSION = Embed()
NO_PERMISSION.add_field(name='Uh oh!',
                        value="You don't have permission to use this command.")


def dashboard_embed(items: List[Tuple[str, str]],
                    title: str, description: str) -> Embed:
    """
    Create a dashboard embed from a list of item IDs.

    :param items: The list of (item ID, rarity) pairs to create a dashboard for.
    :param title: The title of the dashboard.
    :param description: The description of the dashboard.
    :return: None.
    """
    embed = Embed(title=title,
                  description=description + '\n \u200B\n',
                  color=OK_COLOUR,
                  timestamp=datetime.now())
    embed.set_footer(text='\u200B\n'
                          'Changes/medians calculated over past 24 hours')

    # TODO don't actually make it 5 days lol
    day = timedelta(days=5)
    for item_id, rarity in items:
        data = database.get_lbin_history(item_id, rarity, day)
        prices = [tp[1] for tp in data]

        # First row
        begin_price, end_price = prices[0], prices[-1]
        symb = '📈' if end_price >= begin_price else '📉'
        base_name = database.get_base_name(item_id)
        display_rarity = constants.DISPLAY_RARITIES[rarity]
        name = f'{symb} {base_name} ({display_rarity}) → ' \
               f'{utils.format_number(end_price)}'

        # Second/third rows
        abs_change, pct_change = utils.format_change(begin_price, end_price)
        median = statistics.median(prices)
        value = f'→ Change: {abs_change} ({pct_change})\n' \
                f'→ Median: {utils.format_number(median)}\n'

        # Add as a field to the embed
        embed.add_field(name=name, value=value, inline=False)

    return embed
