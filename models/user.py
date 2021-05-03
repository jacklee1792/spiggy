import requests


MOJANG_ENDPOINT = 'https://sessionserver.mojang.com/session/minecraft/profile/'


class User:
    """
    Class defining a Skyblock user.
    """
    uuid: str

    def __init__(self, uuid: str) -> None:
        """
        Create a user instance.

        :param uuid: The UUID of the user.
        """
        self.uuid = uuid

    @property
    def username(self) -> str:
        """
        Get the username of the user from its UUID instance variable.

        This is dangerous right now, ratelimiting + caching needs to be
        implemented later.

        :return: The username of the user.
        """
        res = requests.get(MOJANG_ENDPOINT + self.uuid).json()
        return res['name']
