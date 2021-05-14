import unittest

from backend.parsing import nbtparse

LION_PET_SAMPLE = 'H4sIAAAAAAAAAFVT3W7iRhQekt2uoRdRW2nVSxel1VYbEmz8g5H2IqXQGG' \
                  'GHEJIsVFU1tg8w4LEte5xgql70AfoIveYF+gQ8Sh+k6jHZ/knWaM433znf' \
                  'd8ZnaoRUSYXVCCGVI3LEgsqvFfKyG+eRqNTIsaCLY1K9YgH0Q7rIkPVnjd' \
                  'Ru13kYXj9FkErkyA7IqQktCDRNb7T0cvFNo2FZLa/RnquWClQ3Dd/AvFEa' \
                  'J5AKBlmVSAI2Ik8hO0hL5OU9DXMgv0MxaM7eL5vB+0HoF7aB8eS2GV7bq8' \
                  'S0o/vC69qGzfH86tIYFtZ/uLqgD3o4bQ2Ws+gm9/h9c9gah3A1Vnx+9+hs' \
                  'l3y2umk56mDtTgbM/W7MHO48uXy6mT44mqvOQmfiqK46WM0mvuJuxxzxrb' \
                  'P9hs94f+Vu14q7sovrh6nm8Hs+5b2NHSnW/ObdO+ygRl4FLEtCWlTJi2Gc' \
                  'goTga3Ky37X7cUoXLFrIIxAIfrrfmX1IY5+JoiPvd/StQj5D7FakEC3E8g' \
                  'PWLnPN2wQgeEYszEXIGKWM01DGqj6QN8jB7zIIMiT5b/VzXS83f/z2i/wt' \
                  '5XQBGJk0CshXB+b/GX9LlhwRy0Wcp+Rj3D8BTeIoO/+g2GdpJuQRzgQqvn' \
                  '5WfMawAFsDhmfkFNdJypIQGv+iMipj8WC/C7sx9+LSRRmUntLSGm2ZX5bq' \
                  'HG9MhvkcfMEeoRT+HA/fKBdK8+vy3uQuVirkuwwCPDs9eIAxWyxFww+Zv5' \
                  'bRPg0CWSxZJifIFzH5BCllS4eYQ5R/Uf6n/U5HA72R3ZXIC5dyOFz+98PH' \
                  'UG6ZP6AXfcjiCP/nSW8jUnopsBkvF5BJ5BUWsqN5TIKf6qJIoN6pD+1rt3' \
                  '5Wpwfb9c6chhmc1WGT1DuKajSb+rnaVDVLt6y2bp3VcfRTzCrVMWuJz6qs' \
                  '90+eXzZZ9ojZP0ukGqcMB2dCF0Qa9SY/Oj33TirfKDnGEO3nOe5PDQ+Mud' \
                  'duNywFrIbm6WbD89pawwPPB79NaWDiNFYF45AJyhNyol2o7QtVkY2Opskj' \
                  'h5Aj8tHztJBjQv4CuhzBhhMEAAA='

FOT_SAMPLE = 'H4sIAAAAAAAAAHVUyXLjNhBtj7xImkmczFySVCWBk7FjlzdRkrX4knJkyVaNlxl' \
             'JtmtOLIiERJRJQkWAXo75j+SsqnyGPmU+JJUGQNm+hAeS3XhodDdevyJAARZ4EQ' \
             'AWXsEr7sPGAiy1RBqrhSLkFB0XYJHFXgD6yUHhlPusE9KxRPPfIqz4XE5C+oioM' \
             '5GwPHo34OfZtH7CaEL6HvoOyWzqN2oN/DQ2y+V6fQt+Q8AxjejYLHrbTrmEX7a5' \
             'XS5tGdh25aC0V92C3xHYVwmLxyqw0IN69SW0uXnDVcAS5pNtp1nNdjs7tXptr9T' \
             'Ygl8wQCvhirw87qC0nuGqtfUtTBmt+mwa9kUakjZVLCHd7o6O3goZvWPkGn7QBs' \
             'bhHg3JtV1Lh1xGuIblNtuxj7v62An82PX2A/NSpTe/N9aEJRw7yTC2Dd7hCSNHc' \
             'sI8hT5Yty6pCFbMbxFn45xwGivygYehDm1O60YTGvJ4/BTqjKkAPeoRAd9rWwhl' \
             '1m2Is9S7Jddd+BH/+x5WFI9NjXZzP+I6zS78pI3HSSDi+cYBC9ktj5nkknTBeIJ' \
             'UlxqKxM/qvKbRhCe2FV9pm8UiEqlEE+BX01nvs0iJL0gsFAl0QykJ+DggiEzHgb' \
             '4kr40cwzp10iG7YyFRgqSSESkiRsQI1hCDF02YxUUsVpJgoirA1DD/aA1Pq86mt' \
             'S7+k6Mh1904JKeMqt0+00WMSU9gQCQPXnWve3I6IK2zbuuDoWs/wI5JzCvRGGym' \
             'Ign3hBcwJQ2JhkzdMxbj+SziTO4QXxNKR00nmKsJMpvSiqaSGJFHkSZkJJhcy5i' \
             'nC6hHaaj4JMT9hEoS4XDM4xGaMFhBSMDVHrxDdp7TmJKWkEpztuLU4C06W0KEvr' \
             'iPtY86MmtvfYCNiTTeQzx267krhEtNP52aU9ozvH9KL6IPPEojs3MPu/ctXt7TN' \
             'P0h4lTChp7khOpeY4RtR4/Pl7//JPOZ1OGQ15pz+ppbVFFPREONrptr1HG/w60f' \
             'WTLSPK+X8CH79gtNVAa8jNn0ls6mCZlb+n3+eXDabZHjq4uT9uUF6d9c9o7JMzw' \
             'Pixc0YnCIrqecO6G4R15jfYMkNcnVvvz1z/+9oQir7QeV0COF8zbEUZU5WE0oTv' \
             'mjm07GCfWZVrmFHHwTCOVOhKJKuJ7WRnQX85CPhM9HHOvP32c55OCtn+J0idjV7' \
             'XdNExC9lIeCSDgSZkDH8PWnKySe2+oddQbdi5O8Ed7VztnlTbvnXnbcQe9qcFqE' \
             'Ny/JnoM8z8ZeK3EOFkOcavxdxhUvkyZ9Ug6WPSNbmSHNRKOxmIOV0AqDtZaknnw' \
             'b4p2mZoTa50pUQZdpFcSVVzl4rZ5FwLajIOcaYjPBPFESXGnUz55aZE96ZzGFu7' \
             'lMWMDrEaqfS4362XNWmBVMu/5mrGXPvTWyl7lGWh1dadTRVpC/y8QmC6qe1WneC' \
             'qPS1iiEc5nUNiCH0hQb/37EaIMOveZuhVac3WqjUdodOs3aLm3UmzWvfFCq1kp4' \
             'f9gfJhWWAauV/cZ+2SGOc3hQJh/PMX9YzuYcn/8AunJg11UHAAA='

SA_BOOTS_SAMPLE = 'H4sIAAAAAAAAAH1U3W4bRRQ+jpvWcakaAeIGFaaFSrFCXO/a2bVz59r5k0' \
                  'IceZMCV9Zk99heup4xs7MJueSGVwBVIHFnicfwo+RBEGdm1xENAtvy7pz5' \
                  'vjPf+ZsqwAaU4ioAlNZgLY5KOyVY78lM6FIVyppPNuABinBaIMrJVQJli4' \
                  'QKlODxhbhUyN/yywRLZdg4iiM8SPgkJfhfVXgUxek84Tfk5EQqrJD1OXy+' \
                  'XPiHyBULQrLtseUi8lyPHu0tp9Vwa+AQINAKxURPzXa4vbtLj85WV4QxCs' \
                  '223d2axW87Tafe2q1Bkyg9FWvWm3IRYs5y3Jfv08iw4rVf1sBfkfp8xicF' \
                  'qfUvkn9HajTqTUME6BP1CHmSC+QkyGdHZ/SKW9utBr3W3nfiFyby4jmtut' \
                  's0a2iTlz6OUaSYu+n4uQu3cZ9fkF2Kt92swacmRXPEKOe1C4GduuPmyTgW' \
                  'GpMknmCRDZLYuJfDRuGz5dfbJqZt2qZaLBfJCU81CzQXEXvzlWH1ca6nZF' \
                  'FUXsWOj4/hOVkPkOsprQ84nSQm7FuLPVTymsBvwCzOlNQY6liKwtMQv8+u' \
                  'UHCNhHhChvOpVCK1PgE+WS7Gt7/8zHqJzKKUDTOBdudjEjrEH7JYYcoSvM' \
                  'KEOR7hXywX3kGWJCxAzV5LkaV7LJjySF6zbpryNI0FPDNVlklCMhjJZand' \
                  'T5kcmyV8QdsocBaT5xuZsbcxuYtFSF2dmqDIpqyPyDYJG0tl3ZASvfLxwm' \
                  'xnYoIU5vU0TpBdU38btp7GKUtR1y3GNuXt7z+xVXczc/gVqht7LAX0GRkG' \
                  'glHtcC6V3mNDOkaaqJeLS6cBj+lBkBkXvE7wTUrgqqA2fHvMoeJCp7bojs' \
                  'n57a9/sH/0uS0MweZUOlLU45qHcnZpCL7NrfFMEXumE/YP90/73eF3rH9x' \
                  'erg/OGWvB4PzoAzroUykIiBdAw9O+QyhR4zbd+/YSs+9OpA+aUV5t7/9+V' \
                  '//UIWn+z9qxbuaeu0y05iWYXMq9WguNddyFJqbiQ6tVlYK1ht79K3CuqJm' \
                  'IfTD3sngoh8QpkzSKjMZxeMYFTziua4yfFiUahRrnI1sxIRer8CGVPEkFu' \
                  'd8As+C8+5wuN8fBUfd/uCbUTcI6Hd8OrLhV+z99/+YKnxg7k2qxIxOJWFP' \
                  'IjNEozQfIqOvDB9liY5nNAyjhEaO9mjkjBYKQ9u5yGFVdTc1+e7TcT56o3' \
                  'E+eiYjBJvfTVvhZGJn0SxMmbKMVH8ZdfwOdzq442G4u9OKQr7THkfhDnd5' \
                  '0x+7ru95HcoF6aLW47M5bDruK8d7RfeHv9fy2NnXAGvwsOgl+vwNAk1J8U' \
                  'QGAAA='

BOOK_1_SAMPLE = 'H4sIAAAAAAAAAEWRz27aQBDGx5A2YCVFuVU9Tf8daTDYgeZGiKtUCXZVBUU9' \
                'RYO9mFXttcWuaXiOPoTfww9WdYxos5fdHX3z+77ZtQG6YEkbAKwWtGRs/bbg' \
                'xSwvlbFsaBtKunAkVLSGZrWheyNj8SWlRPP1jw3HsdRFSjtW3eUb0eHqKbyu' \
                'q891FddVukiNzMgIfJBa4Fd4X1fj7yIuI6HRrAXSUqbS7DAjRRjl2mC+gjcs' \
                'MmupURqR4XKHdUXO4CNXPzH+He91Ff3IS4xIYa7SHa5pK9DBf24NIfI5NCmT' \
                'CcVQhSxtcG//E8bTouDWGZtessPI9dB/KvBObEWqD6oFh94neQag3B+naitT' \
                '6DVJc6Q9SZoGflJXKx58Fs7nYdCBo4AyAWdcPOQRMV7l+U+woec/mQ1NjdnI' \
                'ZWmE7kA338hEqntK4HgR3AbhAxP4T+CVH8xupsG9f/14FYa3NpyI5+l0G07L' \
                'w+SPv/idm78Eti5Lbv0w8UYuuYL6EU1GfXfgXPRp5Q778ehiOXYGMXmux9bc' \
                'L7ShrICed+4450MHh5ejCX6bA7Tg5TVllDRk+AtGYHTbMgIAAA=='

BOOK_2_SAMPLE = 'H4sIAAAAAAAAAE1STW/aQBAdIGkAtUTppVXVw/TrVhoIEEJuQKgSJRipCY16' \
                'QoM9wKr2ruVd0/A7+iP4H/ywqmNEk1o+7M6+efve2ykDlCCnygCQy0NeBbnf' \
                'Odjvm1S7XBkKjuYl2GPtLyD7ClC6VAF/DWluZfunDAeBsnFIK0HdmISLUj2C' \
                '15t1Z7MONutwHDoVkWO8V5bxCj5s1u1vHKQ+W3QLRpqqULkVRqQJfWMdmhm8' \
                'EZBbKIvKcYTTFW7WVK99kuoXeCXUPdIsOOwmbpGY2AQWv8NbOb7SfsJkhTug' \
                'iOaMAVPo0BnImuW/jUV9YmX1WUjbfVoy/lfbwkgH2dmtCpeczJRdyGYnorkT' \
                'AfB+y+f/MCn6pNHocIWLjK2O/yxnNvyBJEfaRazFmUaBZp7ePTK0u3EsrX1x' \
                'fi43NJodHDzEeMNLDu0ONZbktnE8EaDaLrt6qUI4zOIySFsm5TLyiojN0vf6' \
                'o+Fw5BVhz6OI4UjKO0UcYM+Yn1CGw8GDS6jrXKKmqWNbhJJJ1FzpO5rDwdi7' \
                '9kb3wiCjAZWB17/seneDi0lvNLouw3N+8mcL8HIqLzMxswk9voyI2S/Ai3QX' \
                'yuSXzEE2ayCa0lQ4P04bs1mrzY1qcFr3q83mSaN61qhx9XTm+y1uU8enQDRJ' \
                'P1tHUQyV1vHZ8Ukdm+fNGnaHAHl4drF972xE/wKV0BmJ0QIAAA=='

RUNE_SAMPLE = 'H4sIAAAAAAAAAD1SwW7aQBAdSNKA26qHqveN1CuS7QCBYzCEOMJ2SgjGvlRre4' \
              'xNFpva64D5gN567ifwA/0CPqUfUnVNpe5t3pt582Z2JIAm1GIJAGp1qMdB7UcN' \
              'LrS0SHhNgjNOl004x8SPoHpn0LyPA7xjdJmL8I8E0tNLwZi1TTBrQF0P4HPY9n' \
              '3Vw26r3+8orWvqtVu9vqK2Qrkt90Llpoudjqh7zNINZjzGvAkNjjteZJifbDTg' \
              'Yk5ZgfALywfZXURysHhgfql3RTx7kpmlrzY3ejIvPU3v6mvB3w/2Vtx7Dcbzdn' \
              'A/L92FUXg2K1zbLB3blSfrDgu0/n+tifq8NVbOtbm/VQx1ujJnX0pzOH9xbEN2' \
              'VkbHsr/szPFd5M70nWs/Xxv2aGvMBrE7ZCtjb6jOPmKOOmcV7o4fmDV2FGusx+' \
              'FC6YsJJLgM4nzDaCl2N0kzbAjwLXw8HnpT/FbEYlDC8BUZUUASoI10kybVQq+O' \
              'hxstQ8qRUOKxNA0IhiH6nGwjTEiZFvBepLzEjJF16uVXooYI4HazYSXhUZyTrE' \
              'iQ8JRs/4mSNDuphkUu4G0qqCXyCDNCuShAMi2S2Id3IuURA8w5ZZXop+MhPB6Y' \
              'ZhmGZRLNejJGM11rwLlJ11ix/u+f38ng5HBaddR1Xcz9YbTjGb3lPIu9glf/eV' \
              'H5yc/gcjCxrOFX9XREjerQ4Hz6bI4A6vBmSNd0iYKAvw5qnm2PAgAA'


class TestParsing(unittest.TestCase):

    def test_lion_pet(self) -> None:
        nbt = nbtparse.deserialize(LION_PET_SAMPLE)
        api_id = nbtparse.extract_api_id(nbt)
        identifiers = nbtparse.extract_identifiers(nbt)
        pet_type = nbtparse.extract_pet_type(nbt)
        pet_exp = nbtparse.extract_pet_exp(nbt)
        pet_candy_used = nbtparse.extract_pet_candy_used(nbt)
        reforge = nbtparse.extract_reforge(nbt)

        self.assertEqual(api_id, 'PET')
        self.assertEqual(identifiers, ('LION_PET', 'Lion Pet', '[Lvl 37] Lion'))
        self.assertEqual(pet_type, 'LION')
        self.assertAlmostEqual(pet_exp, 126005.20249599859)
        self.assertEqual(pet_candy_used, 1)
        self.assertIsNone(reforge)

    def test_fot(self) -> None:
        nbt = nbtparse.deserialize(FOT_SAMPLE)
        identifiers = nbtparse.extract_identifiers(nbt)
        hot_potato_count = nbtparse.extract_hot_potato_count(nbt)
        is_recombobulated = nbtparse.extract_is_recombobulated(nbt)
        reforge = nbtparse.extract_reforge(nbt)
        rarity = nbtparse.extract_rarity(nbt)
        dungeon_stars = nbtparse.extract_dungeon_stars(nbt)
        is_fragged = nbtparse.extract_is_fragged(nbt)
        pet_type = nbtparse.extract_pet_type(nbt)
        pet_exp = nbtparse.extract_pet_exp(nbt)

        self.assertEqual(identifiers, ('FLOWER_OF_TRUTH', 'Flower of Truth',
                                       'Withered Flower of Truth ✪✪✪✪✪'))
        self.assertEqual(hot_potato_count, 10)
        self.assertTrue(is_recombobulated)
        self.assertEqual(reforge, 'withered')
        self.assertEqual(rarity, 'MYTHIC')
        self.assertEqual(dungeon_stars, 5)
        self.assertFalse(is_fragged)
        self.assertIsNone(pet_type)
        self.assertAlmostEqual(pet_exp, 0)

    def test_sa_boots(self) -> None:
        nbt = nbtparse.deserialize(SA_BOOTS_SAMPLE)
        identifiers = nbtparse.extract_identifiers(nbt)
        is_fragged = nbtparse.extract_is_fragged(nbt)
        rune = nbtparse.extract_rune(nbt)

        self.assertEqual(identifiers, ('SHADOW_ASSASSIN_BOOTS',
                                       'Shadow Assassin Boots',
                                       '⚚ Ancient Shadow Assassin Boots ✪✪✪✪✪'))
        self.assertTrue(is_fragged)
        self.assertEqual(rune, ('CLOUDS', 3))

    def test_book_1(self) -> None:
        nbt = nbtparse.deserialize(BOOK_1_SAMPLE)
        api_id = nbtparse.extract_api_id(nbt)
        identifiers = nbtparse.extract_identifiers(nbt)

        self.assertEqual(api_id, 'ENCHANTED_BOOK')
        self.assertEqual(identifiers, ('ULTIMATE_WISE_1_BOOK',
                                       'Ultimate Wise 1 Book',
                                       'Ultimate Wise 1 Book'))

    def test_book_2(self) -> None:
        nbt = nbtparse.deserialize(BOOK_2_SAMPLE)
        identifiers = nbtparse.extract_identifiers(nbt)
        enchants = nbtparse.extract_enchants(nbt)

        self.assertEqual(identifiers, ('ENCHANTED_BOOK', 'Enchanted Book',
                                       'Enchanted Book'))
        self.assertCountEqual(enchants, [('bane_of_arthropods', 5),
                                         ('ultimate_wise', 1)])

    def test_rune(self) -> None:
        nbt = nbtparse.deserialize(RUNE_SAMPLE)
        identifiers = nbtparse.extract_identifiers(nbt)
        rune = nbtparse.extract_rune(nbt)

        self.assertEqual(identifiers, ('BLOOD_2_RUNE_3', 'Blood Rune 3',
                                       '◆ Blood Rune III'))
        self.assertEqual(rune, ('BLOOD_2', 3))


if __name__ == '__main__':
    unittest.main()
