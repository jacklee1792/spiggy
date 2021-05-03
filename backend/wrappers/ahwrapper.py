from typing import Callable, Any


ACTIVE_AUCTIONS_ENDPOINT = 'https://api.hypixel.net/skyblock/auctions'
ENDED_AUCTIONS_ENDPOINT = 'https://api.hypixel.net/skyblock/auctions_ended'

_active_auctions_last_update = 0
_ended_auctions_last_update = 0
_active_auctions_on_update_processes = []
_ended_auctions_on_update_processes = []


def on_active_auctions_update(func: Callable[[Any], Any]) -> None:
    """
    Add a process to be executed when the active auctions page updates.

    :param func: a callable which can optionally take the list of active
    auctions as the keyword argument 'active_auctions'.
    :return: None.
    """
    _active_auctions_on_update_processes.append(func)


def on_ended_auctions_update(func: Callable[[Any], Any]) -> None:
    """
    Add a process to be executed when the ended auctions page updates.

    :param func: a callable which can optionally take the list of ended
    auctions as the keyword argument 'ended_auctions'.
    :return: None.
    """
    _ended_auctions_on_update_processes.append(func)
