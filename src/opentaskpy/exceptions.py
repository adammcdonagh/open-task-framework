"""A bunch of exceptions that can be raised by the opentaskpy package."""
# mypy: ignore-errors


class FileTooNewError(Exception):
    """File too new error."""

    def __init__(self, message):
        """Call the base class constructor."""
        super().__init__(message)


class LogWatchTimeoutError(Exception):
    """Log watch timeout error."""

    def __init__(self, message):
        """Call the base class constructor."""
        super().__init__(message)


class LogWatchInitError(Exception):
    """Log watch init error."""

    def __init__(self, message):
        """Call the base class constructor."""
        super().__init__(message)


class RemoteTransferError(Exception):
    """Remote transfer error."""

    def __init__(self, message):
        """Call the base class constructor."""
        super().__init__(message)


class RemoteFileNotFoundError(Exception):
    """Remote file not found error."""

    def __init__(self, message):
        """Call the base class constructor."""
        super().__init__(message)


class FilesDoNotMeetConditionsError(Exception):
    """Files do not meet conditions error."""

    def __init__(self, message):
        """Call the base class constructor."""
        super().__init__(message)


class DuplicateConfigFileError(Exception):
    """Duplicate config file error."""

    def __init__(self, message):
        """Call the base class constructor."""
        super().__init__(message)


class InvalidConfigError(Exception):
    """Invalid config error."""

    def __init__(self, message):
        """Call the base class constructor."""
        super().__init__(message)


class UnknownProtocolError(Exception):
    """Unknown protocol error."""

    def __init__(self, message):
        """Call the base class constructor."""
        super().__init__(message)


class LookupPluginError(Exception):
    """Lookup plugin error."""

    def __init__(self, message):
        """Call the base class constructor."""
        super().__init__(message)


class VariableResolutionTooDeepError(Exception):
    """Variable resolution too deep error."""

    def __init__(self, message):
        """Call the base class constructor."""
        super().__init__(message)


class SSHClientError(Exception):
    """SSH client error."""

    def __init__(self, message):
        """Call the base class constructor."""
        super().__init__(message)
