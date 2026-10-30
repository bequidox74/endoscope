def rle(bpp: int, fullsize: int, data: bytes) -> bytes:
    return data


def indexed(bpp: int, data: bytes, palette: list[int]) -> bytes:
    return data


def sequential(bpp: int, data: bytes) -> bytes:
    return data


def rgb565(b: bytes) -> int:
    raise NotImplementedError


def rgb888(b: bytes) -> int:
    raise NotImplementedError


def argb8888(b: bytes) -> int:
    return int.from_bytes(b, byteorder="little")
