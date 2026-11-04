import concurrent
import concurrent.futures
import json
import logging
import os
import re
import shutil
import threading
import time
from pathlib import Path
from typing import ClassVar

from endoscope._internal.reader import BinaryReader
from endoscope._internal.utils import (
    check_indir,
    check_infile,
    filter_ranges,
    split_range,
)
from endoscope.data.clib import Clib
from endoscope.data.gamefile import GameData
from endoscope.data.utils import read_gamedata

logger = logging.root


AUDIO_ARRAY_ID_NONE = 4294967295  # -1 in two's complement.
INDEX_FILE_NAME = "sprindex.json"

def views_to_json(pin: Path, minify: bool = True) -> str:
    check_infile(pin)
    gd = read_gamedata(pin)
    out_json = _to_json(gd)

    indent = None if minify else 2
    separators = (",", ":") if minify else (",", ": ")
    return json.dumps(out_json, indent=indent, separators=separators)


def _to_json(gd: GameData) -> list:
    out = []
    for vi, view in enumerate(gd.views):
        view_json: dict = {}
        view_json["id"] = vi + 1
        view_json["name"] = gd.view_names[vi]
        out.append(view_json)

        loops: list = []
        for loop in view.loops:
            out_loop: dict = {}
            frames: list[dict] = []
            out_loop["runNext"] = loop.run_next_loop
            out_loop["frames"] = frames

            for frame in loop.frames:
                out_frame: dict = {}
                out_frame["image"] = frame.image
                if frame.x_offset != 0:
                    out_frame["xOffset"] = frame.x_offset
                if frame.y_offset != 0:
                    out_frame["yOffset"] = frame.y_offset
                if frame.delay != 0:
                    out_frame["delay"] = frame.delay
                if frame.flipped:
                    out_frame["flipped"] = frame.flipped
                if frame.audio_array_id != AUDIO_ARRAY_ID_NONE:
                    out_frame["audioArrayId"] = frame.audio_array_id
                frames.append(out_frame)

            if frames:
                loops.append(out_loop)

        if loops:
            view_json["loops"] = loops
    return out


class ViewsExporter:
    THREADS: ClassVar = 10

    def __init__(self) -> None:
        self.pin: Path
        self.pout: Path
        self.sprdir: Path
        self.include: list[range]
        self.exclude: list[range]
        self.dirs: bool
        self.ext: str | None
        self.move: bool
        self.threads: int
        self.stop: threading.Event

        self._count = 0
        self._spridx_path: Path
        self._index: dict[str, str]
        self._gd: GameData
        self._indices: list[int]

    def export(
        self,
        pin: Path,
        pout: Path,
        sprdir: Path,
        include: list[range],
        exclude: list[range],
        dirs: bool,
        ext: str | None,
        move: bool,
        threads: int,
    ) -> tuple[int, float]:
        self.pin = pin
        self.pout = pout
        self.sprdir = sprdir
        self.include = include
        self.exclude = exclude
        self.dirs = dirs
        self.ext = ext
        self.move = move
        self.threads = threads

        self.stop = threading.Event()
        self._count = 0

        check_infile(self.pin)
        check_indir(self.sprdir)

        if self.ext is not None:
            self.ext = self.ext.removesuffix(".").casefold()

        self._spridx_path = self.sprdir / INDEX_FILE_NAME
        self._prepare_index()

        pclib = Clib.read_file(self.pin)
        clib = pclib.clib
        file = clib[GameData.FILENAME]
        with open(self.pin, "rb") as sin:
            sin.seek(pclib.offset + file.offset)
            br = BinaryReader(sin)
            gd = GameData.read(br)
            self._gd = gd
        logger.info("Loaded game data")

        logger.info("Exporting views...")
        fullrange = range(len(gd.views))
        self._indices = filter_ranges(fullrange, self.include, self.exclude)
        ranges = split_range(0, len(gd.views), self.threads)

        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(self.threads) as executor:
            for i, r in enumerate(ranges):
                logger.debug("Started worker thread %d", i)
                executor.submit(self._export_views, r[0], r[1])
        end = time.time()

        elapsed = end - start
        logger.info(
            "Done processing %d views in %.2f seconds",
            self._count,
            elapsed,
        )
        return self._count, elapsed

    def _export_views(self, start: int, end: int) -> None:
        for i in range(start, end):
            if self.stop.is_set():
                break
            idx = self._indices[i]
            self._export_view(idx)

    def _prepare_index(self) -> None:
        index: dict
        if self._spridx_path.exists():
            logger.info(
                "Found %s, reusing. (Delete to force sprite reindexing.)",
                INDEX_FILE_NAME,
            )
            with open(self._spridx_path, "r", encoding="utf-8") as sin:
                index = json.load(sin)
        else:
            logger.info("Indexing sprites...")
            index = self._build_sprite_index()
            with open(self._spridx_path, "w", encoding="utf-8") as sout:
                json.dump(index, sout)
            logger.info("Index saved to %s", INDEX_FILE_NAME)
        self._index = index

    def _export_view(self, i: int) -> None:
        self._count += 1
        name = self._gd.view_names[i]
        logger.info('Exporting view %d "%s"', i, name)
        view_dir = self.pout / f"{i + 1}_{name}"
        view = self._gd.views[i]

        os.makedirs(view_dir, exist_ok=True)
        for li, loop in enumerate(view.loops):
            if self.stop.is_set():
                break
            if self.dirs:
                loop_dir = view_dir / str(li)
            else:
                loop_dir = view_dir
            os.makedirs(loop_dir, exist_ok=True)

            for fi, frame in enumerate(loop.frames):
                frame_image = str(frame.image)
                try:
                    src_relpath = self._index[frame_image]
                except KeyError:
                    logger.error("Error: sprite %s not found in index", frame_image)
                    continue

                src_abspath = self.sprdir.joinpath(src_relpath)
                suffix = src_abspath.suffix

                out_name = f"{fi}{suffix}"
                if not self.dirs:
                    out_name = f"{li}_{out_name}"

                if self.move:
                    shutil.move(src_abspath, loop_dir / out_name)
                else:
                    shutil.copyfile(src_abspath, loop_dir / out_name)

    def _build_sprite_index(self) -> dict:
        sprdir = self.sprdir
        pattern = re.compile(r"\D*(\d+)$")  # extracts the first number

        out = {}
        for p in sprdir.iterdir():
            if p.is_dir():
                continue  # skip dirs
            if p.stem.startswith("_"):
                continue  # escape hatch for ignoring conflicting files
            if self.ext is not None and not p.suffix.casefold().endswith(self.ext):
                continue  # skip ignored extensions

            m = pattern.match(p.stem)
            if m is None:
                continue  # skip non-matching

            try:
                n = str(int(m.group(1)))
            except ValueError:
                continue

            relpath = str(p.relative_to(sprdir))
            if n in out:
                # force the user to deal with duplicates.
                raise RuntimeError(
                    f"duplicate files: {relpath} and {out[n]}. "
                    "Prefix duplicates with '_' to ignore them."
                )
            out[n] = relpath

        return out


def lookup_sprite(pin: Path, sprid: int) -> None:
    check_infile(pin)
    gd = read_gamedata(pin)

    refs: dict[int, dict[int, list[int]]] = {}
    for vi, view in enumerate(gd.views):
        for loops, loop in enumerate(view.loops):
            for fi, frame in enumerate(loop.frames):
                if frame.image == sprid:
                    refs.setdefault(vi, {}).setdefault(loops, []).append(fi)

    for vi, loops in refs.items():
        if not loops:
            continue
        print(f'View {vi} "{gd.view_names[vi]}":')

        rows: list = []
        for li, frames in loops.items():
            if not frames:
                continue
            for fi in frames:
                rows.append([li, fi])
        for r in rows:
            print(f"  {r[0]} - {r[1]}")
        print()
