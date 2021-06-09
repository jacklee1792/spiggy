import functools
import inspect
import math
import statistics
from configparser import ConfigParser
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Coroutine, List, Optional, Tuple, Union

import discord
import numpy as np
from discord.ext.commands import Cog
from discord_slash import SlashContext, cog_ext
from matplotlib import colors as mcolors, dates as mdates, pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.ticker import FuncFormatter

from backend.database import database
from bot import embeds


_here = Path(__file__).parent
_cfg = ConfigParser()
_cfg.read(_here.parent / 'config/spiggy.ini')

SLASH_COMMAND_GUILDS = _cfg['Bot'].get('SlashCommandGuilds')

if SLASH_COMMAND_GUILDS == '':
    # Register slash commands globally
    SLASH_COMMANDS_GUILDS = None
else:
    # Register slash commands in the given guilds
    SLASH_COMMAND_GUILDS = [int(x) for x in SLASH_COMMAND_GUILDS.split(',')]


def format_number(price: float) -> str:
    """
    Format large numbers to make them more readable with K, M,
    and B suffixes.

    :param price: The price of interest.
    :return: A string containing the price formatted with a suffix.
    """
    is_negative = price < 0
    prefix = '-' if is_negative else ''
    if is_negative:
        price = -price
    cutoffs = [(1e9, 'B'), (1e6, 'M'), (1e3, 'K'), (1, '')]
    for cutoff, suffix in cutoffs:
        if price >= cutoff:
            number = f'{price / cutoff:.2f}'
            while len(number) > 4 or number[-1] == '.':
                number = number[:-1]
            return prefix + number + suffix
    return f'{price:.2f}'


def format_change(begin_price: float, end_price: float) -> Tuple[str, str]:
    """
    Return the absolute price change and percentage price change as a pair of
    strings.

    :param begin_price: The beginning price.
    :param end_price: The ending price.
    :return: A pair of strings representing the absolute and percentage changes.
    """
    abs_change = end_price - begin_price
    pct_change = 100 * abs_change / begin_price
    sign = '+' if abs_change >= 0 else ''
    return sign + format_number(abs_change), f'{abs(pct_change):.2f}%'


def plot_with_gradient(xs: List[datetime], ys: List[float],
                       ax=None, **kwargs) -> None:
    """
    Plot the given lists of x-values and y-values with a gradient color fill
    under it.

    Credit to https://stackoverflow.com/a/29331211
    and https://stackoverflow.com/a/31163913

    :param xs: The list of x-values to plot.
    :param ys: The list of y-values to plot.
    :param ax: The pyplot axes to plot on.
    :return: None.
    """

    xs = np.array([mdates.date2num(x) for x in xs])
    ys = np.array(ys)

    if ax is None:
        ax = plt.gca()

    line, = ax.plot(xs, ys, **kwargs)
    fill_color = line.get_color()

    z_order = line.get_zorder()
    alpha = line.get_alpha()
    alpha = 1.0 if alpha is None else alpha

    z = np.empty((100, 1, 4), dtype=float)
    rgb = mcolors.colorConverter.to_rgb(fill_color)
    z[:, :, :3] = rgb
    z[:, :, -1] = np.linspace(0, alpha, 100)[:, None]

    x_min, x_max = xs.min(initial=None), xs.max(initial=None)
    y_min, y_max = ys.min(initial=None), ys.max(initial=None)
    y_margin = 0.5 * (y_max - y_min)
    im = ax.imshow(z, aspect='auto',
                   extent=[x_min, x_max, y_min - y_margin, y_max],
                   origin='lower', zorder=z_order)

    xy = np.column_stack([xs, ys])
    xy = np.vstack([[x_min, y_min - y_margin], xy, [x_max, y_min - y_margin],
                    [x_min, y_min - y_margin]])
    clip_path = Polygon(xy, facecolor='none', edgecolor='none', closed=True)
    ax.add_patch(clip_path)
    im.set_clip_path(clip_path)

    plt.ylim(y_min - y_margin, y_max + y_margin)


def smoothen(xs: List[Any], ys: List[float]) -> Tuple[List[Any], List[float]]:
    """
    Reduce to ~100 data points and apply smoothing.

    :param xs: The list of x-values.
    :param ys: The list of y-values to have the filter applied to.
    :return: The new x and y values.
    """
    n = len(xs)
    window_size = math.ceil(n / 100)
    new_xs, new_ys = [], []
    for window_start in range(0, n, window_size):
        window_end = window_start + window_size
        new_x = xs[window_start]
        new_y = statistics.median(ys[window_start:window_end])
        new_xs.append(new_x)
        new_ys.append(new_y)
    return new_xs, new_ys


def plot_ah_price(item_id: str, rarity: str,
                  span: timedelta) -> None:
    """
    Plot the historical price of an item and store it in plot.png.

    :param item_id: The item ID to be plotted.
    :param rarity: The rarity of the item to be plotted.
    :param span: The number of previous days to plot.
    :return: None.
    """
    results = database.get_lbin_history(item_id, rarity, span)
    xs, ys = zip(*results)
    xs, ys = smoothen(xs, ys)

    # Theme
    plt.style.use('seaborn-dark')

    # Setup
    plt.clf()
    plt.cla()
    fig, ax = plt.gcf(), plt.gca()
    plt.grid()

    # Titles
    plt.subplots_adjust(top=0.75)
    plt.figtext(0.05, 0.9, f'{item_id} ({rarity})',
                fontweight='bold', fontsize=12, color='slategray')
    begin_price, end_price = ys[0], ys[-1]
    plt.figtext(0.05, 0.85, f'{format_number(end_price)}',
                fontweight='bold', fontsize=12)
    color = 'forestgreen' if end_price >= begin_price else 'darkred'
    abs_change, pct_change = format_change(begin_price, end_price)
    plt.figtext(0.05, 0.8, f'{abs_change} {pct_change}',
                fontweight='bold', fontsize=10, color=color)

    # Price styling
    formatter = FuncFormatter(lambda price, _: format_number(price))
    ax.yaxis.set_major_formatter(formatter)

    # Date formatting
    locator = mdates.AutoDateLocator(minticks=5, maxticks=15)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    # Plot the results and save
    plot_with_gradient(xs, ys)
    here = Path(__file__).parent
    plt.savefig(here / 'plot.png')


async def is_owner(ctx: SlashContext) -> bool:
    return await ctx.bot.is_owner(ctx.author)


def cog_slash(subcommand: bool = False,
              options: Optional[List[Any]] = None,
              checks: Optional[List[Union[Callable, Coroutine]]] = None,
              **slash_kwargs: Any) -> Callable:
    """
    Wrapper for the cog_ext decorators which automatically fills
    in the guild_ids field from the config file. Allows for convenient switching
    between global and guild-local slash commands.

    The decorator also supports adding check functions through the check
    parameter.

    :param subcommand: Whether or not the command defines a subcommand.
    :param options: The slash command options.
    :param checks: The checks to be run before the command is executed. Each
    check should be a function or coroutine which accepts a SlashContext
    parameter and returns a boolean describing whether or not the check was OK.
    :param slash_kwargs: The keyword arguments to be passed to the
    cog_ext.cog_slash decorator.
    :return: None.
    """
    if options is None:
        # Don't keep options as None because cog_ext.cog_slash will introspect
        # on the wrapper
        options = []
    if checks is None:
        checks = []

    def decorator(command):

        # Innermost wrapper which runs the checks
        async def wrapper(self: Cog,
                          ctx: SlashContext, *args, **kwargs) -> None:
            for check in checks:
                if inspect.iscoroutinefunction(check):
                    ok = await check(ctx)
                else:
                    ok = check(ctx)
                if not ok:
                    await ctx.send(embed=embeds.NO_PERMISSION)
                    return
            await command(self, ctx, *args, **kwargs)

        # Decorate the wrapper with the appropriate cog_ext decorator
        if subcommand:
            wrapper = cog_ext.cog_subcommand(guild_ids=SLASH_COMMAND_GUILDS,
                                             options=options,
                                             **slash_kwargs)(wrapper)
        else:
            wrapper = cog_ext.cog_slash(guild_ids=SLASH_COMMAND_GUILDS,
                                        options=options,
                                        **slash_kwargs)(wrapper)

        # Decorate again with functools.wraps
        return functools.wraps(command)(wrapper)
    return decorator
