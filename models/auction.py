from datetime import datetime, timezone
from typing import Any, Dict

from models.item import Item, make_item
from models.user import User


class Auction:
    """
    Abstract class defining a Skyblock auction.
    """
    auction_id: str
    seller: User
    is_bin: bool
    end_time: datetime
    price: float
    item: Item


class EndedAuction(Auction):
    """
    Class defining an auction which has already ended.
    """
    auction_id: str
    seller: User
    is_bin: bool
    end_time: datetime
    price: float
    item: Item

    buyer: User

    def __init__(self, d: Dict[str, Any]) -> None:
        """
        Construct an EndedAuction instance from a dictionary, which is in the
        format specified by the Skyblock ended auctions API.

        :param d: The dictionary corresponding the the ended auction.
        """
        self.auction_id = d['auction_id']
        self.seller = User(d['seller'])
        self.is_bin = d['bin']
        self.end_time = datetime.fromtimestamp(d['timestamp'] / 1000,
                                               tz=timezone.utc)
        self.price = d['price']
        self.item = make_item(d['item_bytes'])


class ActiveAuction(Auction):
    """
    Class defining an auction which has not yet ended.
    """
    auction_id: str
    seller: User
    is_bin: bool
    end_time: datetime
    price: float
    item: Item

    starting_price: float

    def __init__(self, d: Dict[str, any]) -> None:
        """
        Construct an ActiveAuction instance from a dictionary, which is in the
        format specified by the Skyblock active auctions API.
        :param d: The dictionary corresponding to the active auction.
        """
        self.auction_id = d['uuid']
        self.seller = User(d['auctioneer'])
        self.is_bin = 'bin' in d
        self.end_time = datetime.fromtimestamp(d['end'] / 1000, tz=timezone.utc)
        self.price = d['highest_bid_amount']
        self.item = make_item(d['item_bytes'])
        self.starting_price = d['starting_bid']


if __name__ == '__main__':
    # uhhh why doesn't my item import work
    d = {
        'uuid': 'asdf',
        'auctioneer': 'asdf',
        'bin': True,
        'end': 1620101495396,
        'highest_bid_amount': 123123,
        'item_bytes': (
            'H4sIAAAAAAAAACWPwUrDQBRFb9JqkxEUN4K76U8oLpOmolCKtN3LSzOkY6cZybxA+0'
            'X5j3yBXyS+4OrB4ZwLTwEpIqsARDFiWyU/Ea4Wvms4Upgw1ROkb7Yyr47qINavwqyy'
            '4dvRJcV05VuTCJ1hPvTPH472RvPBBm2bIJEm/dUdTenPmj0eRBk7oSUxO6ODb+q55I'
            '9D/5Q7Ciydzqlh08oZFdxrLVl+0duDbY5+bVh8NfQvQ+822WaZYLqmk8GtoP9EFzbs'
            'oXC3PHNLGXNry45NSMb3cJNnu91q+Vm8bxdAjOuCTlQbGcUfet7RKAwBAAA='
        ),
        'starting_bid': 123
    }
    a = ActiveAuction(d)
