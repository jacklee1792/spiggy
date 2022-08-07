import statistics
from datetime import datetime, timedelta
from typing import List, Tuple

from discord import Embed

from backend import constants, database
from bot import embeds, utils


class Dashboard:
    """
    Represents an item dashboard.

    :ivar items: The (item ID, rarity) pairs in the dashboard.
    :ivar message_id: The ID of the message which holds the dashboard.
    :ivar channel_id: The ID of the channel which holds the dashboard.
    :ivar title: The title of the dashboard.
    :ivar description: The description of the dashboard.
    """
    items: List[Tuple[str, str]]
    message_id: int
    channel_id: int
    title: str
    description: str

    def __init__(self, items: List[Tuple[str, str]],
                 message_id: int, channel_id: int, title: str = 'No title set',
                 description: str = 'No description set') -> None:
        """
        Construct a dashboard class instance.

        :param items: The items in the dashboard.
        :param message_id: The ID of the message which holds the dashboard.
        :param channel_id: The ID of the channel which holds the dashboard.
        :param title: The title of the dashboard.
        :param description: The description of the dashboard.
        """
        self.items, self.title, self.description = items, title, description
        self.message_id, self.channel_id = message_id, channel_id

    def get_embed(self) -> Embed:
        """
        Generate the embed object for this dashboard.

        :return: The embed object.
        """
        embed = Embed(title=self.title,
                      description=self.description + '\n \u200B\n',
                      color=embeds.OK_COLOUR,
                      timestamp=datetime.now())
        embed.set_footer(text='\u200B\n'
                              'Changes/medians calculated over past 24 hours')

        day = timedelta(days=1)
        for item_id, rarity in self.items:
            data = database.get_lbin_history(item_id, rarity, day)
            prices = [tp[1] for tp in data]

            base_name = database.get_base_name(item_id) or item_id
            display_rarity = constants.DISPLAY_RARITIES[rarity]

            if len(prices) and base_name != item_id:
                begin_price, end_price = prices[0], prices[-1]
                symb = '📈' if end_price >= begin_price else '📉'
                abs_change, pct_change = utils.format_change(begin_price,
                                                             end_price)
                median = statistics.median(prices)
                value = f'→ Change: {abs_change} ({pct_change})\n' \
                        f'→ Median: {utils.format_number(median)}'
            else:
                symb = '🤔'
                end_price = '??'
                value = '→ No data!'

            name = f'{symb} {base_name} ({display_rarity}) → ' \
                   f'{utils.format_number(end_price)}'

            # Add as a field to the embed
            embed.add_field(name=name, value=value, inline=False)

        return embed
