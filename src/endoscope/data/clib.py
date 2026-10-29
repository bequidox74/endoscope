import io
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, NamedTuple

from endoscope import utils
from endoscope.utils.binary_reader import BinaryReader
from endoscope.utils.check import check


class PlacedClib(NamedTuple):
    clib: Clib
    offset: int


class File(NamedTuple):
    name: str  # cstr
    df_index: int  # u8
    offset: int  # u64
    size: int  # u64

    @staticmethod
    def read(br: BinaryReader) -> File:
        name = br.cstr()
        df_index, offset, size = struct.unpack("<bQQ", br.read(17))
        return File(name, df_index, offset, size)


@dataclass
class Clib:
    SIG_START: ClassVar[bytes] = b"CLIB\x1a"
    SIG_END: ClassVar[bytes] = b"CLIB\x01\x02\x03\x04SIGE"

    version: int  # u8
    df_index: int  # u8
    dfile_names: list[str]  # cstr
    files: list[File]

    def __getitem__(self, key: str) -> File:
        for f in self.files:
            if f.name == key:
                return f
        raise KeyError(f"asset not found: {key}")

    @staticmethod
    def read(br: BinaryReader) -> Clib:
        sig = br.read(len(Clib.SIG_START))
        check(sig == Clib.SIG_START, "CLIB signature mismatch")
        version, df_index = struct.unpack("<bb", br.read(2))
        check(df_index == 0, "non-zero data file index")
        br.skip(4)
        dfile_names: list[str] = [br.cstr() for _ in range(br.u32())]
        files: list[File] = [File.read(br) for _ in range(br.u32())]

        return Clib(
            version=version,
            df_index=df_index,
            dfile_names=dfile_names,
            files=files,
        )

    @staticmethod
    def read_file(path: Path) -> PlacedClib:
        type_ = utils.detect_file_type(path)
        if type_ == "exe":
            return Clib.read_exe(path)
        else:
            with open(path, "rb") as s:
                br = BinaryReader(s)
                return PlacedClib(Clib.read(br), 0)

    @staticmethod
    def read_exe(path: Path) -> PlacedClib:
        with open(path, "rb") as s:
            br = BinaryReader(s)
            s.seek(-(len(Clib.SIG_END) + 8), io.SEEK_END)
            offset = br.u64()
            sig = s.read(len(Clib.SIG_END))
            check(sig == Clib.SIG_END, "CLIB end signature mismatch")

            s.seek(offset)
            return PlacedClib(Clib.read(br), offset)
