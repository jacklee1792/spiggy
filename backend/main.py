import time
import requests
from models import item as asdf
from database import database


LAST_UPDATED = 0
ENDPOINT = 'https://api.hypixel.net/skyblock/auctions_ended'

if __name__ == '__main__':
    while True:
        res = requests.get(ENDPOINT).json()
        if res['lastUpdated'] == LAST_UPDATED:
            continue

        LAST_UPDATED = res['lastUpdated']
        lst = []
        for auction in res['auctions']:
            item = asdf.make_item(auction['item_bytes'])
            price = auction['price']
            lst.append((item, price))

        database.save_ended_auctions(lst)
        print(f'OK read {len(lst)} items')
        time.sleep(15)
