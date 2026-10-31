import numpy as np

# these dogshit sprites are stored as little endian ARGB on the disk.
_PERM = [2, 1, 0, 3]  # ARGB (BGRA in LE) -> RGBA


def to_rgba(data: bytes) -> bytes:
    pix = np.frombuffer(data, dtype=np.uint8).reshape(-1, 4)
    return pix[:, _PERM].tobytes()


def rle(bpp: int, size: int, data: bytes) -> bytes:
    chunks = []
    append = chunks.append
    n = len(data)
    si = 0
    di = 0  # destination index, in elements

    while di < size:
        if si >= n:
            raise ValueError("RLE input truncated")
        cx = data[si]  # unsigned 0..255
        si += 1
        if cx > 128:  # run: signed -127..-1
            i = 257 - cx
            nb = bpp
            if si + nb > n:
                raise ValueError("RLE input truncated")
            if di + i > size:
                raise ValueError("RLE buffer overflow")
            append(data[si : si + nb] * i)
        else:  # sequence: 0..127, and 128 (-128) acts like 0
            i = (cx & 127) + 1
            nb = i * bpp
            if si + nb > n:
                raise ValueError("RLE input truncated")
            if di + i > size:
                raise ValueError("RLE buffer overflow")
            append(data[si : si + nb])
        si += nb
        di += i

    return b"".join(chunks)


def argb8888(b: bytes) -> int:
    return int.from_bytes(to_rgba(b), "little")


def indexed(palette: list[int]) -> np.ndarray:
    return np.frombuffer(
        b"".join(v.to_bytes(4, "little") for v in palette), dtype=np.uint8
    ).reshape(len(palette), 4)


def indexed_to_rgba(data: bytes, palette: list[int]) -> bytes:
    return indexed(palette)[np.frombuffer(data, dtype=np.uint8)].tobytes()


def sequential(data: bytes) -> bytes:
    return to_rgba(data)
