class ResponseCodeError(Exception):
    """
    Called when the Skyblock API returns an unexpected response code.

    :ivar status_code: The status code which was received.
    """
    def __init__(self, status_code: int):
        self.status_code = status_code


class MalformedResponseError(Exception):
    """
    Called when the Skyblock API returns a response which is malformed.
    """
    pass


class UnexpectedUpdateError(Exception):
    """
    Called when the Skyblock API updates during a cache.
    """
    pass
