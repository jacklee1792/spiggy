import asyncio
import configparser
import logging
import os
from pathlib import Path

import discord
import dotenv
from discord.ext import commands
from discord_slash import SlashCommand

from backend.controllers.auctionhouse import AuctionHouse
from backend.controllers.bazaar import Bazaar
from backend.controllers.skyblockapi import SkyblockAPI
from backend.database import database
from bot.cogs.auctionscog import AuctionsCog
from bot.cogs.metacog import MetaCog


async def main() -> None:
    # Set up logging
    logging.basicConfig(level=logging.INFO,
                        format='[%(asctime)s] %(funcName)s > %(levelname)s: '
                               '%(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')
    logging.getLogger('discord').setLevel(logging.WARNING)
    logging.getLogger('discord_slash').setLevel(logging.WARNING)

    # Read config
    config_folder = Path(__file__).parent.parent / 'config'
    config = configparser.ConfigParser()
    config.read(config_folder / 'spiggy.ini')

    # Initialize bot/slash command handler
    bot = commands.Bot(command_prefix='???',
                       intents=discord.Intents.default())
    SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True)

    # Tokens
    dotenv.load_dotenv(dotenv_path=config_folder / '.env')
    spiggy_token = os.getenv('SPIGGY_BOT_TOKEN')
    hypixel_key = os.getenv('HYPIXEL_API_KEY')

    async with SkyblockAPI(hypixel_key) as api:
        ah = AuctionHouse(api)
        bz = Bazaar(api)

        # Load cogs
        bot.add_cog(MetaCog(bot=bot))
        bot.add_cog(AuctionsCog(bot=bot, ah=ah))

        # On every active auctions cache, update item ID to base name
        # mappings and rarity counts
        ah.on('active auctions cache', database.save_item_info)

        # When the lowest BIN buffer is ready, save it to the database and
        # update all of the dashboards
        ah.on('lbin buffer ready', database.save_lbin_history)
        ah.on('lbin buffer ready', bot.cogs['AuctionsCog'].refresh_dashboards)

        # When the sale buffer is ready, save it tot he database
        ah.on('sale buffer ready', database.save_avg_sale_history)

        # Start all processes
        await asyncio.gather(ah.start_caching(),
                             bz.start_caching(),
                             bot.start(spiggy_token))

if __name__ == '__main__':
    asyncio.run(main())
