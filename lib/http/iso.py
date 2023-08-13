import hashlib
import os
import typing

from . import HttpHandler
from ..iso import IsoBase


class IsoHttpHandler(HttpHandler):
    def __init__(self, prefix: str):
        if not os.path.isdir(prefix):
            raise ValueError(f'prefix {prefix} is not a directory')

        cdimage = os.path.join(prefix, 'cdimage')
        mapfile = os.path.join(prefix, 'mapfile')
        if not os.path.isfile(cdimage):
            raise ValueError(f'cdimage {cdimage} is not a file')

        if not os.path.isfile(mapfile):
            mapfile = None

        self.prefix = prefix
        self.iso = IsoBase(cdimage, mapfile)
        self._checksum_map: dict[str, bytes] = {}

    def close(self):
        self.iso.close()

    def exists(self, path: str) -> bool:
        return path in self.iso.path_map

    def file_sz(self, path: str) -> int:
        return self.iso.path_map[path].inode.data_length

    def checksum(self, path: str) -> typing.Optional[bytes]:
        return self._checksum_map.get(path, None)

    def read_bytes(self, path: str) -> typing.Generator[bytes, None, None]:
        dr = self.iso.path_map[path]
        sz = dr.inode.fp_offset + dr.inode.data_length

        m = None
        if path not in self._checksum_map:
            m = hashlib.sha256()

        for step in range(dr.inode.fp_offset, sz, 4096):
            chunk = self.iso.mm[step:min(step + 4096, sz)]
            if m is not None:
                m.update(chunk)
            yield chunk

        if m is not None:
            self._checksum_map[path] = m.digest()
