import colorsys

import numpy as np

from endoscope._internal.reader import BinaryReader

N = 4096
F = 16
MASK_N = N - 1

# these dogshit sprites are stored as little endian ARGB on the disk.
_PERM = [2, 1, 0, 3]  # ARGB (BGRA in LE) -> RGBA


def palette_256() -> list[int]:
    palette = []
    for i in range(256):
        h = (i * 0.61803398875) % 1.0  # golden ratio hue step
        s = 0.55 + 0.45 * ((i * 0.7548776662) % 1.0)  # vary saturation
        v = 0.55 + 0.45 * ((i * 0.5698402910) % 1.0)  # vary brightness
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        palette.append(int.from_bytes((
            int(r * 255),
            int(g * 255),
            int(b * 255),
        )))
    palette[0] = 0
    return palette


PALETTE256 = palette_256()


def to_rgba(data: bytes) -> bytes:
    pix = np.frombuffer(data, dtype=np.uint8).reshape(-1, 4)
    return pix[:, _PERM].tobytes()


def to_rgb(data: bytes) -> bytes:
    return data


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


def rle_online(bpp: int, size: int, br: BinaryReader) -> tuple[bytes, int]:
    if bpp not in (1, 2, 4):
        raise ValueError(f"Illegal BPP: {bpp}")

    read = br.read
    chunks = []
    append = chunks.append
    si = 0
    di = 0

    while di < size:
        cx = read(1)[0]
        si += 1

        if cx > 128:  # run
            n = 257 - cx
            di += n * bpp
            if di > size:
                raise ValueError("RLE buffer overflow")
            si += bpp
            append(read(bpp) * n)
        else:  # sequence
            n = 1 if cx == 128 else cx + 1
            nbytes = n * bpp
            di += nbytes
            if di > size:
                raise ValueError("RLE buffer overflow")
            si += nbytes
            append(read(nbytes))

    return b"".join(chunks), si


# port of lzwexpand (actually LZSS) in Common/util/lzw.cpp with optimizations.
# used primarily for room backgrounds.
def lzw(src: bytes, dst_sz: int) -> tuple[bool, bytes]:  # -> (ok, dst)
    src_sz = len(src)
    if dst_sz == 0:
        return False, b""

    lz = bytearray(N)  # LZSS ring buffer
    dst = bytearray(dst_sz)  # output buffer
    src_ptr = 0
    dst_ptr = 0
    i = N - F  # index into the ring buffer, must match encoder

    # while we still have space:
    while src_ptr < src_sz and dst_ptr < dst_sz:
        bits = src[src_ptr]  # 8 control bits, LE order (0 - literal, 1 - backref)
        src_ptr += 1

        # fast path for all 0 bits (literal copy)
        if bits == 0 and src_ptr + 8 <= src_sz and dst_ptr + 8 <= dst_sz:
            chunk = src[src_ptr : src_ptr + 8]
            src_ptr += 8
            dst[dst_ptr : dst_ptr + 8] = chunk
            dst_ptr += 8

            # ring buffer stuff
            e = i + 8
            if e <= N:  # enough space to copy directly
                lz[i:e] = chunk
            else:  # otherwise, split and write parts
                k = N - i
                lz[i:] = chunk[:k]
                lz[: e - N] = chunk[k:]
            i = e & MASK_N  # advance i modulo (N - 1)
            continue

        # mask (control bits) loop
        mask = 0x01
        while mask & 0xFF:  # after 8 iters the low byte will overflow
            # control bit:
            if bits & mask:  # 1 - backref
                if src_ptr > src_sz - 2:  # need 2 bytes from src
                    break
                j = src[src_ptr] | (src[src_ptr + 1] << 8)  # construct an i16
                src_ptr += 2

                # backref length (bits 12-15 (4)). lengths range 3-18;
                # less is below the break-even point and less inefficient.
                length = ((j >> 12) & 15) + 3
                # offset in the ring buffer modulo (N - 1) (bits 0-11 (12)).
                # high bits (length) discarded by &.
                j = (i - j - 1) & MASK_N

                if dst_ptr > dst_sz - length:
                    break  # not enough space in dst

                d = (i - j) & MASK_N  # match distance (0 means N)

                # fast path for copying
                if d == 0 or d >= length:  # source already populated: plain copy
                    e = j + length
                    if e <= N:
                        chunk = lz[j:e]
                    else:
                        chunk = lz[j:] + lz[: e - N]
                else:  # overlap: repeat first d bytes
                    e = j + d  # ring buffer stuff
                    if e <= N:
                        seed = lz[j:e]
                    else:
                        seed = lz[j:] + lz[: e - N]
                    chunk = (seed * (length // d + 1))[:length]

                dst[dst_ptr : dst_ptr + length] = chunk
                dst_ptr += length

                # ring buffer stuff, same as before.
                e = i + length
                if e <= N:
                    lz[i:e] = chunk
                else:
                    k = N - i
                    lz[i:] = chunk[:k]
                    lz[: e - N] = chunk[k:]
                i = e & MASK_N

            # 0 - literal
            else:
                if src_ptr >= src_sz:
                    break  # not enough data in src
                ch = src[src_ptr]
                src_ptr += 1
                lz[i] = ch  # copy
                dst[dst_ptr] = ch
                dst_ptr += 1
                i = (i + 1) & MASK_N  # advance i modulo (N - 1)

            if dst_ptr >= dst_sz or src_ptr >= src_sz:
                break  # ran out of space

            mask <<= 1  # next control bit

    return src_ptr == src_sz, dst[:dst_ptr].take_bytes()


def argb8888(b: bytes) -> int:
    return int.from_bytes(to_rgba(b), "little")


def _indexed_rgba(palette: list[int]) -> np.ndarray:
    return np.frombuffer(
        b"".join(v.to_bytes(4, "little") for v in palette), dtype=np.uint8
    ).reshape(len(palette), 4)


def _indexed_rgb(palette: list[int]) -> np.ndarray:
    return np.frombuffer(
        b"".join(v.to_bytes(3, "big") for v in palette), dtype=np.uint8
    ).reshape(len(palette), 3)


def indexed_to_rgba(data: bytes, palette: list[int]) -> bytes:
    return _indexed_rgba(palette)[np.frombuffer(data, dtype=np.uint8)].tobytes()


def indexed_to_rgb(data: bytes, palette: list[int]) -> bytes:
    return _indexed_rgb(palette)[np.frombuffer(data, dtype=np.uint8)].tobytes()


def sequential(data: bytes) -> bytes:
    return to_rgba(data)
