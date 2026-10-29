import io
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import ClassVar, NamedTuple

from endoscope.utils.binary_reader import BinaryReader
from endoscope.utils.check import check


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
class CLib:
    SIG_START: ClassVar[bytes] = b"CLIB\x1a"
    SIG_END: ClassVar[bytes] = b"CLIB\x01\x02\x03\x04SIGE"

    version: int  # u8
    df_index: int  # u8
    dfile_names: list[str]  # cstr
    files: list[File]

    @staticmethod
    def read(br: BinaryReader) -> CLib:
        sig = br.read(len(CLib.SIG_START))
        check(sig == CLib.SIG_START, "CLIB signature mismatch")
        version, df_index = struct.unpack("<bb", br.read(2))
        check(df_index == 0, "non-zero data file index")
        br.skip(4)
        dfile_names: list[str] = [br.cstr() for _ in range(br.u32())]
        files: list[File] = [File.read(br) for _ in range(br.u32())]

        return CLib(
            version=version,
            df_index=df_index,
            dfile_names=dfile_names,
            files=files,
        )

    @staticmethod
    def read_exe(path: Path) -> tuple[CLib, int]:
        with open(path, "rb") as s:
            br = BinaryReader(s)
            s.seek(-(len(CLib.SIG_END) + 8), io.SEEK_END)
            offset = br.u64()
            sig = s.read(len(CLib.SIG_END))
            check(sig == CLib.SIG_END, "CLIB end signature mismatch")

            s.seek(offset)
            return CLib.read(br), offset
