from abc import ABC, abstractmethod


class TaskHandler(ABC):
    def __init__(self, spec):
        self.spec = spec

    @abstractmethod
    def return_result(self, status, mesaage, exception):
        ...

    @abstractmethod
    def _set_remote_handlers(self):
        ...

    @abstractmethod
    def run(self):
        ...
