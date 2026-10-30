import itertools
import logging
from pathlib import Path
from typing import BinaryIO, Iterable, Literal

SUFFIXES = (".exe", ".ags", ".vox")

logger = logging.getLogger(__name__)


def check(cond: bool, message: str, *args) -> None:
    if not cond:
        raise AssertionError(message % args)


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


def parse_ranges(s: str | None) -> list[range]:
    if s is None:
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


def check_dir(p: Path) -> None:
    check(p.exists(), "directory %s does not exist", p)
    check(p.is_dir(), "%s is not a directory", p)
    if "Program Files" in str(p):
        logger.warning(
            "Warning: you seem to be writing to Program Files, "
            "which is probably NOT what you want. If this IS what "
            "you want, make sure you are running as admin!"
        )


def check_datafile(p: Path) -> None:
    check(p.is_file(), "%s is not a file", p)
    check(p.suffix.casefold() in SUFFIXES, "%s is not a supported data file", p)
