import mmap
import os.path
from io import BytesIO

import pycdlib
from pycdlib.dr import DirectoryRecord


def parse_mapfile_lines(lines: list[str]):
    for line in lines:
        if line.startswith('#'):
            continue
        parts = [x.strip() for x in line.split(' ') if x.strip() != '']
        if len(parts) != 3:
            continue
        pos, size, status = parts
        if status not in ['+', '-']:
            continue
        yield int(pos, 0), int(size, 0), status == '+'


def overlap(a: range, b: range) -> bool:
    return a.start <= b.stop and b.start <= a.stop


class IsoBase:
    def __init__(self, cdimage: str, mapfile: str):
        self.cdimage = cdimage
        self.mapfile = mapfile
        self.iso = pycdlib.PyCdlib()
        self.iso.open(self.cdimage)

        self.fp = open(cdimage, 'rb')
        self.mm = mmap.mmap(self.fp.fileno(), 0, access=mmap.ACCESS_READ)

        with open(self.mapfile, 'r') as fp:
            mapfile_lines = fp.readlines()
        self.read_errors = list(
            map(lambda x: range(x[0], x[0] + x[1]),
                list(filter(lambda x: not x[2], parse_mapfile_lines(mapfile_lines))))
        )

        if self.iso.has_joliet():
            self.facade = 'joliet'
            self.fz = self.iso.get_joliet_facade()
            self.fz_kw = 'joliet_path'
            self.fz_filename = lambda dr: dr.file_identifier().decode('utf-16-be')
        elif self.iso.has_rock_ridge():
            self.facade = 'rock_ridge'
            self.fz = self.iso.get_rock_ridge_facade()
            self.fz_kw = 'rock_ridge_path'
            self.fz_filename = lambda dr: dr.file_identifier().decode('utf-8')
        elif self.iso.has_udf():
            self.facade = 'udf'
            self.fz = self.iso.get_udf_facade()
            self.fz_kw = 'udf_path'
            self.fz_filename = lambda dr: dr.file_identifier().decode('utf-8')
        else:
            self.fz = self.iso.get_iso9660_facade()
            self.fz_kw = 'iso_path'
            self.fz_filename = lambda dr: dr.file_identifier().decode('utf-8')

        self.path_map: dict[str, DirectoryRecord] = {}
        self.path_errors = []

        self._populate_path_map()

        print(f'initialized cdimage={cdimage}, mapfile={mapfile} with '
              f'facade={self.facade},'
              f'read_errors={self.read_errors},'
              f'path_errors={self.path_errors}')

    def _populate_path_map(self):
        for dr, path, filename in self.walk('/'):
            if dr.is_file():
                abspath = os.path.join(path, filename).removesuffix(';1')
                if self.has_read_error(dr):
                    self.path_errors.append(abspath)
                self.path_map[abspath] = dr

    def close(self):
        self.iso.close()
        self.mm.close()
        self.fp.close()

    def has_read_error(self, dr: DirectoryRecord) -> bool:
        if len(self.read_errors) == 0:
            return False

        if dr.is_file():
            return any([overlap(range(dr.fp_offset, dr.fp_offset + dr.data_length), x) for x in self.read_errors])
        return False

    def walk(self, path: str, depth: int = 0):
        child: DirectoryRecord
        for child in self.fz.list_children(**{self.fz_kw: path}):
            if child.is_dot() or child.is_dotdot():
                continue

            filename = self.fz_filename(child)
            yield child, path, filename

            # recurse into directories
            if child.is_dir():
                for abc in self.walk(os.path.join(path, filename), depth + 1):
                    yield abc
