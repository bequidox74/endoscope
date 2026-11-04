import itertools
import json
import logging
from pathlib import Path
from typing import BinaryIO, Literal

SUFFIXES = (".exe", ".ags", ".vox")

logger = logging.getLogger(__name__)


def check(cond: bool, message: str, *args) -> None:
    if not cond:
        raise ValueError(message % args)


class ChunkedCopy:
    def __init__(self) -> None:
        self.stop = False

    def copy(
        self,
        src: BinaryIO,
        dst: BinaryIO,
        offset: int,
        size: int,
        chunk_size: int = 64 * 1024,
    ) -> None:
        src.seek(offset)
        copied: int = 0
        while copied < size:
            if self.stop:
                return
            left = size - copied
            chunk = src.read(min(chunk_size, left))
            dst.write(chunk)
            copied += len(chunk)


def detect_file_type(path: Path) -> Literal["clib", "exe"]:
    if path.suffix == ".exe":
        return "exe"
    else:
        return "clib"


def parse_ranges(s: str | None) -> list[range]:
    if s is None or not s:
        return []

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


def filter_ranges(full: range, include: list[range], exclude: list[range]) -> list[int]:
    filters = exclude if exclude else include
    filtered = itertools.chain.from_iterable(filters)
    if not filters:
        return list(full)
    check(bool(include) != bool(exclude), "both include and exclude specified")

    if exclude:
        s = set(filtered)
        return [i for i in full if i not in s]
    else:
        return list(filtered)


def split_range(start: int, end: int, n: int) -> list[tuple[int, int]]:
    if n <= 0:
        raise ValueError("n must be positive")
    total = end - start
    if total < 0:
        raise ValueError("end must be >= start")
    n = min(n, total)  # can't make more non-empty chunks than elements

    base, rem = divmod(total, n)
    chunks = []
    pos = start
    for i in range(n):
        size = base + (1 if i < rem else 0)
        chunks.append((pos, pos + size))
        pos += size
    return chunks


def check_indir(p: Path) -> None:
    check(p.exists(), "directory %s does not exist", p)
    check(p.is_dir(), "%s is not a directory", p)


def check_infile(p: Path) -> None:
    check(p.exists(), "file %s does not exist", p)
    check(not p.is_dir(), "%s is not a file", p)


def is_program_files(p: Path) -> bool:
    return "Program Files" in str(p)


def dump_json(obj: dict, minify: bool = False) -> str:
    indent = None if minify else 2
    sep = (",", ":") if minify else (",", ": ")
    return json.dumps(obj, indent=indent, separators=sep)


def check_datafile(p: Path) -> None:
    check(
        is_datafile(p),
        f"{p} is not a data file. Only {', '.join(SUFFIXES)} are supported.",
    )


def is_datafile(p: Path) -> bool:
    return p.suffix.casefold() in SUFFIXES
