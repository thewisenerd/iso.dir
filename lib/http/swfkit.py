import os.path
import typing
import zlib

from . import HttpHandler
from ..swfkit import SwfKitBase


class SwfKitHttpHandler(HttpHandler):
    def __init__(self, prefix: str, exe: str):
        abs_exe = os.path.join(prefix, exe)
        self.kit = SwfKitBase(abs_exe)

    def close(self):
        self.kit.close()

    def exists(self, path: str) -> bool:
        return path in self.kit.files

    def file_sz(self, path: str) -> int:
        return self.kit.files[path].raw_sz

    def checksum(self, path: str) -> bytes:
        return self.kit.files[path].sha256

    def read_bytes(self, path: str) -> typing.Generator[bytes, None, None]:
        file = self.kit.files[path]

        dat = zlib.decompress(self.kit.mm[file.offset:file.offset + file.zlib_sz])
        yield dat
