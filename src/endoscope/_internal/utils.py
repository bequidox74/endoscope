from pathlib import Path
from typing import BinaryIO, Literal


def check(cond: bool, message: str, *args) -> None:
    if not cond:
        raise AssertionError(str.format(message, *args))


def chunked_copy(
    src: BinaryIO,
    dst: BinaryIO,
    offset: int,
    size: int,
    chunk_size: int = 64 * 1024,
) -> None:
    src.seek(offset)
    copied: int = 0
    while copied < size:
        left = size - copied
        chunk = src.read(min(chunk_size, left))
        dst.write(chunk)
        copied += len(chunk)


def detect_file_type(path: Path) -> Literal["clib", "exe"]:
    if path.suffix == ".exe":
        return "exe"
    else:
        return "clib"


def parse_ranges(s: str) -> list[range]:
    result: list[range] = []
    parts = s.split(",")
    check(len(parts) > 0, "attempt to parse empty range spec")

    # collect
    for p in parts:
        check(bool(p), "empty range part")
        bounds = p.split("-")
        if len(bounds) == 1:
            i = int(p)
            result.append(range(i, i + 1))
        elif len(bounds) == 2:
            start, end = int(bounds[0]), int(bounds[1])
            result.append(range(start, end + 1))
        else:
            raise ValueError("range spec item must be of form 'n' or 'm-n'")

    if not result:
        return result

    # sort & merge
    result.sort(key=lambda r: r.start)
    merged: list[range] = [result[0]]
    for r in result[1:]:
        last = merged[-1]
        if r.start < last.stop:
            merged[-1] = range(last.start, max(last.stop, r.stop))
        else:
            merged.append(r)

    return merged
