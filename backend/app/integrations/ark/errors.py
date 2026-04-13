class ArkError(Exception):
    """Base Ark integration error."""


class ArkConfigError(ArkError):
    """Raised when Ark settings are incomplete."""


class ArkAuthenticationError(ArkError):
    """Raised when Ark rejects authentication."""


class ArkRateLimitError(ArkError):
    """Raised when Ark rate limits the request."""


class ArkResponseError(ArkError):
    """Raised when Ark returns a non-success response."""


class ArkResponseParseError(ArkError):
    """Raised when Ark output cannot be parsed into the expected shape."""


class ArkToolUnavailableError(ArkError):
    """Raised when the configured Ark tool is unavailable."""
