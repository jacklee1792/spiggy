class ResponseCodeError(Exception):
    """
    Called when the Skyblock API returns an unexpected response code.
    """
    pass


class UnexpectedUpdateError(Exception):
    """
    Called when the Skyblock API updates during a cache.
    """
    pass
