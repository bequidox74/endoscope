import logging
import os
from argparse import ArgumentParser, Namespace
from fnmatch import fnmatch
from pathlib import Path

from endoscope._internal import utils
from endoscope._internal.utils import check_dir, check_exe
from endoscope.data.clib import Clib

logger = logging.getLogger(__name__)

CHUNK_SIZE_KIB = 64


def init_parser(subp) -> None:
    parser: ArgumentParser = subp.add_parser(
        "unpack",
        help="unpack assets",
    )

    parser.add_argument(
        "input",
        type=Path,
        help="input file (.exe, .ags, .vox)",
    )
    parser.add_argument(
        "output",
        type=Path,
        help="output directory (will be created if needed)",
    )

    parser.add_argument(
        "-c",
        "--chunk-size",
        default=CHUNK_SIZE_KIB,
        type=int,
        help=f"chunk size in KiB for copying (default is {CHUNK_SIZE_KIB})",
    )
    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="do a dry run without writing any files (effectively lists assets)",
    )

    filters = parser.add_mutually_exclusive_group()
    filters.add_argument(
        "-i",
        "--include",
        nargs="+",
        help="wildcards for included files (can have multiple)",
    )
    filters.add_argument(
        "-e",
        "--exclude",
        nargs="+",
        help="wildcards for excluded files (can have multiple)",
    )

    parser.set_defaults(func=main)


def main(args: Namespace) -> None:
    unpack(
        pin=args.input,
        pout=args.output,
        include=args.include,
        exclude=args.exclude,
        chunk_size=args.chunk_size,
        dry_run=args.dry_run,
    )


def unpack(
    pin: Path,
    pout: Path,
    include: list[str],
    exclude: list[str],
    chunk_size: int,
    dry_run: bool,
) -> None:
    check_exe(pin)
    check_dir(pout)

    clib, off_clib = Clib.read_file(pin)
    logger.info("CLIB v%d listing %d files", clib.version, len(clib.files))
    count = 0
    for f in clib.files:
        if not _filter(f.name, include, exclude):
            continue

        if not dry_run:
            pout_full = pout / f.name
            os.makedirs(pout_full.parent, exist_ok=True)
            with open(pin, "rb") as sin, open(pout / f.name, "wb") as sout:
                offset = off_clib + f.offset
                utils.chunked_copy(sin, sout, offset, f.size, chunk_size)

        count += 1
        prefix = "Would have extracted" if dry_run else "Extracted"
        logger.info("%s '%s' (%d bytes)", prefix, f.name, f.size)
    logger.info("Done. %d assets extracted to %s", count, pout)


def _filter(fname: str, inc: list[str], exc: list[str]) -> bool:
    if inc:
        return any(fnmatch(fname, f) for f in inc)
    elif exc:
        return not any(fnmatch(fname, f) for f in exc)
    else:
        return True
