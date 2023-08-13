import hashlib
import mmap
import os.path
import struct
import zlib
from dataclasses import dataclass

import pefile


@dataclass
class SwfKitFile:
    name: str
    offset: int
    zlib_sz: int
    raw_sz: int
    sha256: bytes


def parse_file(mm: mmap.mmap, start: int) -> tuple[SwfKitFile, int]:
    filename = bytearray()
    mm.seek(start)
    while True:
        char = mm.read(2)
        if char == b'\x00\x00':
            break

        filename.extend(char)

    (zlib_sz,) = struct.unpack('i', mm.read(4))
    zlib_offset = mm.tell()
    filename_str = filename.decode('utf-16').encode('utf-8').decode()
    print(filename_str, hex(zlib_sz))

    zlib_raw = zlib.decompress(mm.read(zlib_sz))
    raw_sz = len(zlib_raw)
    m = hashlib.sha256()
    m.update(zlib_raw)
    print(f"  zlib.sz={hex(raw_sz)}")
    print(f"  zlib.sha256={m.hexdigest()}")
    print(f"    offset={hex(mm.tell())}")

    meta_unknown = mm.read(8)
    print(f"  meta.unknown={meta_unknown.hex()}")

    return SwfKitFile(filename_str, zlib_offset, zlib_sz, raw_sz, m.digest()), mm.tell()


class SwfKitBase:
    """
    a SWFKit packaged exe has four sections;
    after the end of the sections, the remaining data is some form of an archive.
    the format is as follows,
    1. 48 bytes of unknown data, with the first 3 bytes being 'SAF'
    2. a list of files, each file entry is as follows,
        1. a null-terminated UTF-16 string, the file name
        2. a 4-byte integer, the size of the zlib compressed data
        3. the zlib compressed data
        4. 8 bytes of unknown data

    The exe, upon start, extracts these files to the folder: %temp%/F7B555EB-BC32-486A-8484-B6BEC8318E87/_extra
    """

    def __init__(self, exe: str):
        if not os.path.isfile(exe):
            raise ValueError(f'exe {exe} is not a file')
        self.exe = exe

        pe = pefile.PE(exe)
        exe_eof = 0
        for section in pe.sections:
            section_end = section.PointerToRawData + section.SizeOfRawData
            if section_end > exe_eof:
                exe_eof = section_end
        self.exe_eof = exe_eof

        self.fp = open(exe, 'rb')
        self.mm = mmap.mmap(self.fp.fileno(), 0, access=mmap.ACCESS_READ)

        assert self.mm[exe_eof:exe_eof + 3] == b'SAF', f"{exe} is probably not a executable"

        self.files: dict[str, SwfKitFile] = {}
        start = exe_eof + 48
        while True:
            file, new_start = parse_file(self.mm, start)
            if new_start >= self.mm.size():
                break
            start = new_start
            self.files['/' + file.name] = file

    def close(self):
        self.mm.close()
