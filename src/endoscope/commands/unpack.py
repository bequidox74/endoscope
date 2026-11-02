import logging
import os
import time
from argparse import ArgumentParser, Namespace
from fnmatch import fnmatch
from pathlib import Path

from endoscope._internal import utils
from endoscope._internal.utils import check, check_indir, check_infile
from endoscope.commands.command import Command, command
from endoscope.data.clib import Clib

logger = logging.root

CHUNK_SIZE_KIB = 64


@command("unpack", "unpack game assets")
class UnpackCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
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

    def execute(self, args: Namespace) -> None:
        AssetUnpacker(
            pin=args.input,
            pout=args.output,
            include=args.include,
            exclude=args.exclude,
            chunk_size=args.chunk_size,
            dry_run=args.dry_run,
        ).unpack()


class AssetUnpacker:
    def __init__(
        self,
        pin: Path,
        pout: Path,
        include: list[str],
        exclude: list[str],
        chunk_size: int,
        dry_run: bool,
    ) -> None:
        self.stop = False  # flag for killing the extractor
        self.pin = pin
        self.pout = pout
        self.include = include
        self.exclude = exclude
        self.chunk_size = chunk_size
        self.dry_run = dry_run

    def unpack(
        self,
    ) -> tuple[int, float]:
        pin = self.pin
        pout = self.pout
        include = self.include
        exclude = self.exclude
        chunk_size = self.chunk_size
        dry_run = self.dry_run
        cc = utils.ChunkedCopy()

        check_infile(pin)
        check_indir(pout)
        check(chunk_size > 0, "chunk size cannot be zero")

        clib, off_clib = Clib.read_file(pin)
        logger.info("CLIB v%d listing %d files", clib.version, len(clib.files))
        count = 0
        start = time.time()
        for f in clib.files:
            if self.stop:
                cc.stop = True  # also tell the copy to stop
                break
            if not _filter(f.name, include, exclude):
                continue

            if not dry_run:
                pout_full = pout / f.name
                os.makedirs(pout_full.parent, exist_ok=True)
                with open(pin, "rb") as sin, open(pout / f.name, "wb") as sout:
                    offset = off_clib + f.offset
                    cc.copy(sin, sout, offset, f.size, chunk_size)

            count += 1
            logger.info("Extracted '%s' (%d bytes)", f.name, f.size)
        end = time.time()
        logger.info("Done extracting %d assets in %.2f seconds", count, end - start)
        return count, end - start


def _filter(fname: str, inc: list[str], exc: list[str]) -> bool:
    if not inc and not exc:
        return True
    if inc:
        return any(fnmatch(fname, f) for f in inc)
    elif exc:
        return not any(fnmatch(fname, f) for f in exc)
    else:
        return True
