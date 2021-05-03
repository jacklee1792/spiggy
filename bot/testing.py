import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import FuncFormatter

from backend.database import database


def format_price(price: float) -> str:
    """
    Format the price of a given item in a more human-readable way, using
    K, M, and B suffixes.

    :param price: The price of interest.
    :return: A string containing the price formatted with a suffix.
    """
    cutoffs = [(1e9, 'B'), (1e6, 'M'), (1e3, 'K'), (1, '')]
    for cutoff, suffix in cutoffs:
        if price >= cutoff:
            number = f'{price / cutoff:.2f}'
            while len(number) > 4 or number[-1] == '.':
                number = number[:-1]
            return number + suffix
    return f'{price:.2f}'


if __name__ == '__main__':
    item_id = input('Enter item ID: ') or 'FARMING_FOR_DUMMIES'
    rarity = input('Enter rarity: ') or 'EPIC'

    results = database.get_historical_price(item_id, rarity)

    # Theme
    plt.style.use('seaborn-dark')

    fig, ax = plt.subplots()

    # Date styling
    ax.set_title(f'{item_id} ({rarity})')
    plt.grid()

    # Price styling
    formatter = FuncFormatter(lambda price, _: format_price(price))
    ax.yaxis.set_major_formatter(formatter)

    # Date formatting
    locator = mdates.AutoDateLocator(minticks=5, maxticks=8)
    formatter = mdates.ConciseDateFormatter(locator)
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)

    # Plot the results
    plt.plot(*zip(*results))

    # Fix y-axis
    ax.set_ylim(bottom=0)

    plt.show()
