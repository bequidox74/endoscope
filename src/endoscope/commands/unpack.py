import logging
import os
import threading
import time
from fnmatch import fnmatch
from pathlib import Path
from typing import ClassVar

from endoscope._internal import utils
from endoscope._internal.utils import check, check_indir, check_infile
from endoscope.data.clib import Clib
from endoscope.data.gamefile import GameData
from endoscope.data.utils import read_gamedata

logger = logging.getLogger(__name__)


class AssetUnpacker:
    CHUNK_SIZE_KIB: ClassVar = 64

    def __init__(
        self,
    ) -> None:
        self.pin: Path
        self.pout: Path
        self.include: list[str]
        self.exclude: list[str]
        self.chunk_size: int
        self.dry_run: bool
        self.stop: threading.Event

        self._audio_index: dict[str, str] = {}

    def _build_audio_index(self, gd: GameData) -> None:
        index = {}
        for clip in gd.audio_clips:
            index[clip.file_name] = clip.script_name
        self._audio_index = index

    def unpack(
        self,
        pin: Path,
        pout: Path,
        include: list[str],
        exclude: list[str],
        chunk_size: int,
        dry_run: bool,
    ) -> tuple[int, float]:
        self.pin = pin
        self.pout = pout
        self.include = include
        self.exclude = exclude
        self.chunk_size = chunk_size
        self.dry_run = dry_run
        self.stop = threading.Event()
        cc = utils.ChunkedCopy()

        check_infile(pin)
        check_indir(pout)
        check(chunk_size > 0, "chunk size cannot be zero")

        gd = read_gamedata(pin)
        self._build_audio_index(gd)

        clib, off_clib = Clib.read_file(pin)
        logger.info("CLIB v%d listing %d files", clib.version, len(clib.files))
        count = 0
        start = time.time()
        for f in clib.files:
            if self.stop.is_set():
                cc.stop.set()
                break
            if not _filter(f.name, include, exclude):
                continue

            pout_full = pout / f.name
            if f.name in self._audio_index:
                pout_full = pout_full.with_stem(self._audio_index[f.name])

            if not dry_run:
                os.makedirs(pout_full.parent, exist_ok=True)
                with open(pin, "rb") as sin, open(pout_full, "wb") as sout:
                    offset = off_clib + f.offset
                    cc.copy(sin, sout, offset, f.size, chunk_size)

            count += 1
            logger.info("Extracted '%s' (%d bytes)", pout_full.name, f.size)
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
