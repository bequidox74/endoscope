import io
import struct
from typing import BinaryIO

ENCODING = "latin-1"


class BinaryReader:
    def __init__(
        self,
        stream: BinaryIO,
    ) -> None:
        self.stream = stream

    def read(self, size: int = -1) -> bytes:
        return self.stream.read(size)

    def tell(self) -> int:
        return self.stream.tell()

    def skip(self, size: int) -> None:
        self.stream.seek(size, io.SEEK_CUR)

    def seek(self, to: int, whence: int = io.SEEK_SET) -> None:
        self.stream.seek(to, whence)

    def peek(self, size: int = 0) -> bytes:
        pos = self.stream.tell()
        data = self.stream.read(size)
        self.stream.seek(pos)
        return data

    def byte(self) -> int:
        return self.stream.read(1)[0]

    def i8(self) -> int:
        v = self.stream.read(1)
        return struct.unpack("<b", v)[0]

    def u8(self) -> int:
        v = self.stream.read(1)
        return struct.unpack("<B", v)[0]

    def i16(self) -> int:
        v = self.stream.read(2)
        return struct.unpack("<h", v)[0]

    def u16(self) -> int:
        v = self.stream.read(2)
        return struct.unpack("<H", v)[0]

    def i32(self) -> int:
        v = self.stream.read(4)
        return struct.unpack("<i", v)[0]

    def u32(self) -> int:
        v = self.stream.read(4)
        return struct.unpack("<I", v)[0]

    def i64(self) -> int:
        v = self.stream.read(8)
        return struct.unpack("<q", v)[0]

    def u64(self) -> int:
        v = self.stream.read(8)
        return struct.unpack("<Q", v)[0]

    def f32(self) -> float:
        v = self.stream.read(4)
        return struct.unpack("<f", v)[0]

    def f64(self) -> float:
        v = self.stream.read(8)
        return struct.unpack("<d", v)[0]

    def cstr(self) -> str:
        data = bytearray()
        while True:
            b = self.byte()
            if b == 0:
                break
            data.append(b)
        return bytes(data).decode(ENCODING)

    # Pascal string (length prefixed)
    def pstr(self, strip: bool = True) -> str:
        l = self.u32()
        data = self.stream.read(l)
        if strip:
            data = data.rstrip(b"\x00")
        return data.decode(ENCODING)

    # fixed size string
    def fstr(self, size: int, strip: bool = True) -> str:
        data = self.stream.read(size)
        if strip:
            data = data.rstrip(b"\x00")
        return data.decode(ENCODING)
