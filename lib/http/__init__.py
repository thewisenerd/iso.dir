import typing
from abc import ABC, abstractmethod


class HttpHandler(ABC):
    @abstractmethod
    def close(self):
        pass

    @abstractmethod
    def exists(self, path: str) -> bool:
        pass

    def file_sz(self, path: str) -> int:
        pass

    def checksum(self, path: str) -> typing.Optional[bytes]:
        pass

    def read_bytes(self, path: str) -> typing.Generator[bytes, None, None]:
        pass
