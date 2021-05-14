import numpy as np

from matplotlib import pyplot as plt, colors as mcolors, dates as mdates
from matplotlib.ticker import FuncFormatter
from matplotlib.patches import Polygon
from datetime import datetime
from pathlib import Path
from typing import List

from backend.database import database


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

    x_min, x_max, y_min, y_max = xs.min(), xs.max(), ys.min(), ys.max()
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


def plot_ah_price(item_id: str, span: int) -> None:
    """
    Plot the historical price of an item and store it in plot.png.

    :param item_id: The item ID to be plotted.
    :param span: The number of previous days to plot.
    :return: None.
    """
    rarity = database.guess_rarity(item_id)
    results = database.get_historical_price(item_id, rarity, span)
    xs, ys = zip(*results)

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
    price_change = end_price - begin_price
    percent_change = 100 * price_change / begin_price
    sign = '+' if price_change >= 0 else ''
    color = 'forestgreen' if price_change >= 0 else 'darkred'
    plt.figtext(0.05, 0.8, f'{sign + format_number(price_change)} '
                           f'({percent_change:+.2f}%)',
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
