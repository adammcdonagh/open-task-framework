from abc import ABC, abstractmethod


class RemoteTransferHandler(ABC):
    def __init__(self, spec, remote_spec=None):
        self.spec = spec
        self.remote_spec = remote_spec

    @abstractmethod
    def list_files(self):
        ...

    @abstractmethod
    def transfer_files(self, files, dest_remote_handler=None):
        ...

    @abstractmethod
    def push_files_from_worker(self, files, dest_remote_handler=None):
        ...

    @abstractmethod
    def pull_files_to_worker(self, files, local_staging_directory):
        ...

    @abstractmethod
    def pull_files(self, files):
        ...

    @abstractmethod
    def move_files_to_final_location(self, files):
        ...

    @abstractmethod
    def handle_post_copy_action(self, files):
        ...


class RemoteExecutionHandler(ABC):
    def __init__(self, spec):
        self.spec = spec

    @abstractmethod
    def execute(self, command):
        ...
