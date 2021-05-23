import configparser
import logging
import os
from pathlib import Path

import discord
import dotenv
from discord.ext import commands
from discord_slash import SlashCommand


def main() -> None:
    # Forget about the Discord logging
    logging.getLogger('discord').setLevel(logging.ERROR)

    # Add timestamp to logs
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')

    # Read config
    config_folder = Path(__file__).parent.parent / 'config'
    config = configparser.ConfigParser()
    config.read(config_folder / 'spiggy.ini')

    # Initialize bot/slash command handler
    bot = commands.Bot(command_prefix='???',
                       intents=discord.Intents.default())
    SlashCommand(bot, sync_commands=True, sync_on_cog_reload=True)

    # Load extensions
    bot.load_extension('cogs.metacog')
    bot.load_extension('cogs.auctionscog')

    # Load token, run bot
    dotenv.load_dotenv(dotenv_path=config_folder / '.env')
    token = os.getenv('SPIGGY_BOT_TOKEN')
    bot.run(token)


if __name__ == '__main__':
    main()
