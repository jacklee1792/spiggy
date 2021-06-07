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

        # Auction house handlers
        ah.on_active_auctions(ah.update_active_buffers)
        ah.on_ended_auctions(ah.update_ended_buffers)
        ah.on_active_auctions(database.save_item_info)

        # Load cogs
        bot.add_cog(MetaCog(bot=bot))
        bot.add_cog(AuctionsCog(bot=bot, ah=ah))

        # Start all processes
        await asyncio.gather(ah.start_caching(),
                             bz.start_caching(),
                             bot.start(spiggy_token))

if __name__ == '__main__':
    asyncio.run(main())
