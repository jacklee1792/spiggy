import configparser
import logging
import os
from pathlib import Path

import discord
import dotenv
from discord.ext import commands


def main():
    # Forget about the Discord logging
    logging.getLogger('discord').setLevel(logging.ERROR)

    # Add timestamp to logs
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')

    # Read config
    config_folder = Path(__file__).parent.parent / 'config'
    config = configparser.ConfigParser()
    config.read(config_folder / 'bot.ini')

    command_prefix = config['bot']['command_prefix']
    bot = commands.Bot(command_prefix=command_prefix,
                       intents=discord.Intents.default())

    bot.load_extension('cogs.meta')
    bot.load_extension('cogs.ah')
    dotenv.load_dotenv(dotenv_path=config_folder / '.env')
    token = os.getenv('SPIGGY_BOT_TOKEN')
    bot.run(token)


if __name__ == '__main__':
    main()
