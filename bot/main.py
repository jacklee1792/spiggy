import discord
import logging
import os
import configparser

from discord.ext import commands
from dotenv import load_dotenv


def main():
    logging.getLogger('discord').setLevel(logging.ERROR)
    logging.basicConfig(format='[%(asctime)s] %(levelname)s: %(message)s',
                        datefmt='%m/%d/%Y %I:%M:%S %p')

    config = configparser.ConfigParser()
    config.read('../config/bot.ini')

    logging_level = config['Spiggy']['logging_level']
    logging.getLogger().setLevel(getattr(logging, logging_level))

    command_prefix = config['Spiggy']['command_prefix']
    bot = commands.Bot(command_prefix=command_prefix,
                       intents=discord.Intents.default())

    bot.load_extension('cogs.auctionhouse')
    load_dotenv(dotenv_path='../config/.env')
    token = os.getenv('DISCORD_BOT_TOKEN')
    bot.run(token)


if __name__ == '__main__':
    main()
