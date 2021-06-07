from typing import Any, Dict


class BazaarProduct:
    """
    Class defining bazaar product information at a point in time.
    """
    item_id: str
    buy_price: float
    sell_price: float
    buy_volume: float
    sell_volume: float

    def __init__(self, item_id: str, d: Dict[str, Any]) -> None:
        self.item_id = item_id
        self.buy_price = d['quick_status']['buyPrice']
        self.sell_price = d['quick_status']['sellPrice']
        self.buy_volume = d['quick_status']['buyVolume']
        self.sell_volume = d['quick_status']['sellVolume']
