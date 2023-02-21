# Define a FileTooNewException
class FileTooNewError(Exception):
    def __init__(self, message):
        # Call the base class constructor
        super().__init__(message)


class LogWatchTimeoutError(Exception):
    def __init__(self, message):
        # Call the base class constructor
        super().__init__(message)


class LogWatchInitError(Exception):
    def __init__(self, message):
        # Call the base class constructor
        super().__init__(message)


class RemoteTransferError(Exception):
    def __init__(self, message):
        # Call the base class constructor
        super().__init__(message)


class RemoteFileNotFoundError(Exception):
    def __init__(self, message):
        # Call the base class constructor
        super().__init__(message)


class FilesDoNotMeetConditionsError(Exception):
    def __init__(self, message):
        # Call the base class constructor
        super().__init__(message)


class DuplicateConfigFileError(Exception):
    def __init__(self, message):
        # Call the base class constructor
        super().__init__(message)


class UnknownProtocolError(Exception):
    def __init__(self, message):
        # Call the base class constructor
        super().__init__(message)
