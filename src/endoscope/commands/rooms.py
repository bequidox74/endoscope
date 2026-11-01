import itertools
import logging
import os
import time
from argparse import ArgumentParser, Namespace
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from fnmatch import fnmatch
from pathlib import Path

from PIL import Image

from endoscope._internal.binary_reader import BinaryReader
from endoscope._internal.utils import check, check_dir
from endoscope.commands.command import Command, command
from endoscope.data import decode
from endoscope.data.room import Room

TARGETS = ("backgrounds", "regions", "hotspots", "walkareas")

logger = logging.root


@command("rooms", "room operations")
class RoomsCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "roomdir",
            type=Path,
            help="directory with room (.crm) files",
        )
        subp = parser.add_subparsers(required=True)
        _BitmapsCommand().init_parser(subp)


@command("bitmaps", "extract room bitmaps")
class _BitmapsCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("output", type=Path, help="output directory")
        parser.add_argument(
            "what",
            nargs="*",
            help="what to export",
            choices=TARGETS,
        )

        parser.add_argument(
            "-t",
            "--threads",
            type=int,
            help="number of threads to use (default: 10)",
            default=10,
        )
        parser.add_argument(
            "-d",
            "--dry-run",
            action="store_true",
            help="perform a dry run without creating files",
        )
        parser.add_argument(
            "-g",
            "--glob",
            help="file name glob pattern (e.g. *.crm)",
            default="*.crm",
        )
        parser.add_argument(
            "-x",
            "--extension",
            help="extension to save the files with (e.g. png, jpg, tga, tiff, etc.)",
            default="png",
        )

    def execute(self, args: Namespace) -> None:
        BitmapExtractor(
            args.roomdir,
            args.what,
            args.output,
            args.threads,
            args.dry_run,
            args.glob,
            args.extension,
        )


class BitmapExtractor:
    def __init__(
        self,
        roomdir: Path,
        what: set[str],
        pout: Path,
        nthreads: int,
        dry_run: bool,
        glob: str,
        extension: str,
    ) -> None:
        self.roomdir = roomdir
        self.what = what
        self.pout = pout
        self.nthreads = nthreads
        self.dry_run = dry_run
        self.glob = glob
        self.ext = extension

        check_dir(roomdir)
        os.makedirs(pout, exist_ok=True)

        room_files: list[Path] = []
        for p in roomdir.iterdir():
            if not fnmatch(p.name, glob):
                continue  # skip masked files
            room_files.append(p)
        logger.debug("Found %d matching files", len(room_files))
        if not room_files:
            logger.info("No files to process, exiting")

        self.openfiles: set[Path] = set()
        start = time.time()
        with ThreadPoolExecutor(nthreads) as executor:
            bsize = len(room_files) // nthreads
            if bsize == 0:
                bsize = 1
            for batch in itertools.batched(room_files, bsize):
                executor.submit(self._process_batch, batch)
        end = time.time()
        logger.info(
            "Done processing %d rooms in %.2f seconds",
            len(room_files),
            end - start,
        )

    def _process_batch(self, batch: Iterable[Path]) -> None:
        what = self.what
        for p in batch:
            logger.debug("Processing room %s", p.name)
            if p in self.openfiles:
                raise RuntimeError
            with open(p, "rb") as sin:
                try:
                    br = BinaryReader(sin)
                    room = Room.read(br)
                    if not what or "backgrounds" in what:
                        self._extract_bg(p.stem, br, room)
                        sin.seek(0)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.exception(
                        "Error while processing room %s", p.name, exc_info=exc
                    )

    def _extract_bg(self, name: str, br: BinaryReader, rm: Room) -> None:
        mainblk = rm.blocks[Room.BlockType.MAIN]
        bmoffset = mainblk[1] + rm.off_bitmaps
        br.seek(bmoffset)

        br.skip(256 * 4)  # palette
        origsize = br.u32()
        compsize = br.u32()
        raw = br.read(compsize)
        ok, decomp = decode.lzw(raw, origsize)
        check(ok, "LZW decompression failed")
        decomp = decomp[8:]
        bitmap = decode.sequential(decomp)

        out_path = self.pout / f"{name}/bg.{self.ext}"
        os.makedirs(out_path.parent, exist_ok=True)
        img = Image.frombuffer(
            "RGBA",
            (rm.width, rm.height),
            bitmap,
        ).convert("RGB")

        if not self.dry_run:
            img.save(out_path)
            logger.debug("Saved %s", out_path)
