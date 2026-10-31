import concurrent
import concurrent.futures
import logging
import os
import time
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path

from PIL import Image

from endoscope._internal.binary_reader import BinaryReader
from endoscope._internal.utils import (
    check,
    check_datafile,
    filter_ranges,
    parse_ranges,
    split_range,
)
from endoscope.commands.command import Command, command
from endoscope.data.clib import Clib
from endoscope.data.spriteset import Sprite, SpriteIndex, SpriteSet

logger = logging.getLogger(__name__)


@command("sprites", "extract sprites")
class SpritesCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("input", type=Path, help="input data file")
        parser.add_argument("output", type=Path, help="output directory")

        parser.add_argument(
            "-x",
            "--extension",
            help=(
                "extension to save the sprites with "
                "(most should work, but some may lose transparency)"
            ),
            default="png",
        )
        parser.add_argument(
            "-d",
            "--dry-run",
            action="store_true",
            help="perform a dry run without modifying files",
        )
        parser.add_argument(
            "-t",
            "--threads",
            type=int,
            help="number of threads to use for sprite extraction (10 is usually enough)",
            default=10,
        )

        filters_group = parser.add_mutually_exclusive_group()
        filters_group.add_argument(
            "-i",
            "--include",
            help="comma-separated list or ranges to include (e.g. 1-2,4-7,9)",
        )
        filters_group.add_argument(
            "-e",
            "--exclude",
            help="comma-separated list or ranges to exclude (e.g. 1-2,4-7,9)",
        )

    def execute(self, args: Namespace) -> None:
        SpriteExtractor(
            pin=args.input,
            pout=args.output,
            include=parse_ranges(args.include),
            exclude=parse_ranges(args.exclude),
            dry_run=args.dry_run,
            extension=args.extension,
            threads=args.threads,
        )


class SpriteExtractor:
    def __init__(
        self,
        pin: Path,
        pout: Path,
        include: list[range],
        exclude: list[range],
        dry_run: bool,
        extension: str,
        threads: int,
    ) -> None:
        self.pin = pin
        self.pout = pout
        self.include = include
        self.exclude = exclude
        self.dry_run = dry_run
        self.extension = extension

        check_datafile(pin)
        pclib = Clib.read_file(pin)
        clib = pclib.clib

        ### Read sprite set and sprite index ###
        self.sprset_file = clib[SpriteSet.FILENAME]
        self.spridx_file = clib[SpriteIndex.FILENAME]
        with open(pin, "rb") as sin:
            # read sprite set
            sin.seek(pclib.offset + self.sprset_file.offset)
            br = BinaryReader(sin)
            sprset = SpriteSet.read(br)
            self.sprset = sprset
            logger.info("Loaded spriteset data")

            # read index
            sin.seek(pclib.offset + self.spridx_file.offset)
            spridx = SpriteIndex.read(br)
            self.spridx = spridx
            logger.info("Loaded sprite index")
        self.off_sprset = pclib.offset + self.sprset_file.offset

        check(sprset.spr_file_id == spridx.spr_file_id, "sprite file ID mismatch")
        ts = datetime.fromtimestamp(sprset.spr_file_id)
        logger.info("Sprite file created at %s", ts)

        ### Check that the files match ###
        logger.debug("Last slot (sprset): %d", sprset.last_slot)
        logger.debug("Last slot (spridx): %d", spridx.last_slot)
        logger.debug("Num sprites (spridx): %d", spridx.count)
        logger.debug("Len (spridx): %d", len(spridx.offsets))
        check(sprset.last_slot == spridx.last_slot, "last slots do not match")
        check(sprset.last_slot == spridx.count - 1, "sprite counts do not match")
        self.num_sprites = spridx.count

        ### Process sprites ###
        start = time.time()
        self.indices = filter_ranges(range(self.num_sprites), include, exclude)
        os.makedirs(pout, exist_ok=True)
        ranges = split_range(0, len(self.indices), threads)
        with concurrent.futures.ThreadPoolExecutor(
            len(self.indices) // threads
        ) as executor:
            for i, r in enumerate(ranges):
                executor.submit(self._process_files, r[0], r[1], i)
        end = time.time()
        logger.info(
            "Done. Exported %d sprites in %.2f seconds", self.num_sprites, end - start
        )

    def _process_files(self, start: int, end: int, id_: int):
        logger.debug("Started worker thread %d", id_)
        with open(self.pin, "rb") as sin:
            br = BinaryReader(sin)
            for i in range(start, end):
                idx = self.indices[i]
                if idx >= self.num_sprites:
                    break  # can't trust that the user will put in adequate numbers.

                off_sprite = self.off_sprset + self.spridx.offsets[idx]
                sin.seek(off_sprite)

                sprite = Sprite.read_slot(
                    self.sprset.version, self.sprset.compression, br
                )
                if sprite is None:
                    continue

                sin.seek(off_sprite + sprite.off_data)
                bitmap = sprite.read_bitmap(br)
                file_path = self.pout / f"{idx}.{self.extension}"
                if not self.dry_run:
                    _save_bitmap(bitmap, sprite.width, sprite.height, file_path)
                logger.info("Extracted %s", file_path)


def _save_bitmap(bitmap: bytes, w: int, h: int, p: Path) -> None:
    try:
        image = Image.frombytes("RGBA", (w, h), bitmap)
        if p.suffix.casefold() in (".jpg", ".JPEG"):
            image = image.convert("RGB")
        image.save(p)
    except Exception as exc:
        logger.error("Error while saving sprite %s", p, exc_info=exc)
