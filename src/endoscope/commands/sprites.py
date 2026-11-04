import concurrent
import concurrent.futures
import logging
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import ClassVar

from PIL import Image

from endoscope._internal.reader import BinaryReader
from endoscope._internal.utils import (
    check,
    check_infile,
    filter_ranges,
    split_range,
)
from endoscope.data.clib import Clib, File
from endoscope.data.spriteset import Sprite, SpriteIndex, SpriteSet

logger = logging.getLogger(__name__)


class SpriteExtractor:
    DEFAULT_THREADS: ClassVar = 10

    pin: Path
    pout: Path
    include: list[range]
    exclude: list[range]
    dry_run: bool
    extension: str
    threads: int

    _sprset_file: File
    _spridx_file: File
    _sprset: SpriteSet
    _spridx: SpriteIndex
    _off_sprset: int
    _nsprites: int
    _count: int
    _indices: list[int]

    def __init__(self) -> None:
        self.stop: threading.Event

    def extract(
        self,
        pin: Path,
        pout: Path,
        include: list[range],
        exclude: list[range],
        dry_run: bool,
        extension: str,
        threads: int,
    ) -> tuple[int, float]:
        self.pin = pin
        self.pout = pout
        self.include = include
        self.exclude = exclude
        self.dry_run = dry_run
        self.extension = extension
        self.threads = threads
        self.stop = threading.Event()

        check_infile(pin)
        pclib = Clib.read_file(pin)
        clib = pclib.clib

        ### Read sprite set and sprite index ###
        self._sprset_file = clib[SpriteSet.FILENAME]
        self._spridx_file = clib[SpriteIndex.FILENAME]
        with open(pin, "rb") as sin:
            # read sprite set
            sin.seek(pclib.offset + self._sprset_file.offset)
            br = BinaryReader(sin)
            sprset = SpriteSet.read(br)
            self._sprset = sprset
            logger.debug("Loaded spriteset data")

            # read index
            sin.seek(pclib.offset + self._spridx_file.offset)
            spridx = SpriteIndex.read(br)
            self._spridx = spridx
            logger.debug("Loaded sprite index")
        self._off_sprset = pclib.offset + self._sprset_file.offset

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
        self._nsprites = spridx.count

        ### Process sprites ###
        os.makedirs(pout, exist_ok=True)

        self._indices = filter_ranges(range(self._nsprites), include, exclude)
        ranges = split_range(0, len(self._indices), threads)

        start = time.time()
        self._count = 0
        with concurrent.futures.ThreadPoolExecutor(threads) as executor:
            for i, r in enumerate(ranges):
                executor.submit(self._process_files, r[0], r[1], i)
        end = time.time()

        elapsed = end - start
        logger.info("Done. Exported %d sprites in %.2f seconds", self._count, elapsed)
        return self._count, elapsed

    def _process_files(self, start: int, end: int, id_: int):
        logger.debug("Started worker thread %d", id_)
        with open(self.pin, "rb") as sin:
            br = BinaryReader(sin)
            for i in range(start, end):
                if self.stop.is_set():
                    break

                idx = self._indices[i]
                if idx >= self._nsprites:
                    break  # can't trust that the user will put in adequate numbers.

                off_sprite = self._off_sprset + self._spridx.offsets[idx]
                sin.seek(off_sprite)
                sprite = Sprite.read_slot(
                    self._sprset.version, self._sprset.compression, br
                )
                if sprite is None:
                    continue  # empty slots may theoretically appear.

                file_path = self.pout / f"{idx}.{self.extension}"
                sin.seek(off_sprite + sprite.off_data)

                try:
                    bitmap = sprite.read_bitmap(br)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.exception(
                        "Error while reading bitmap of %s",
                        file_path,
                        exc_info=exc,
                    )
                    continue

                self._save_bitmap(bitmap, sprite.width, sprite.height, file_path)
                self._count += 1
                logger.info("Extracted %s", file_path)

    def _save_bitmap(self, bitmap: bytes, w: int, h: int, p: Path) -> None:
        if self.dry_run:
            return
        try:
            image = Image.frombytes("RGBA", (w, h), bitmap)
            if p.suffix.casefold() in (".jpg", ".JPEG"):
                image = image.convert("RGB")
            image.save(p)
            logger.debug("Saved %s", p)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            logger.exception("Error while saving sprite %s", p, exc_info=exc)
