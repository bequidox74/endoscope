from pathlib import Path
from typing import BinaryIO, Literal


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
