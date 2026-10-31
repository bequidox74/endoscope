import concurrent
import concurrent.futures
import json
import logging
import os
import re
import shutil
import time
from argparse import ArgumentParser, Namespace
from pathlib import Path

from tabulate import tabulate

from endoscope._internal.binary_reader import BinaryReader
from endoscope._internal.utils import (
    check_datafile,
    check_dir,
    filter_ranges,
    parse_ranges,
    split_range,
)
from endoscope.commands.command import Command, command
from endoscope.data.clib import Clib
from endoscope.data.gamefile import GameData
from endoscope.data.utils import read_gamedata

logger = logging.getLogger(__name__)


AUDIO_ARRAY_ID_NONE = 4294967295  # -1 in two's complement.
INDEX_FILE_NAME = "sprindex.json"

_LOOP_HEADERS = ["loop", "run next"]
_FRAME_HEADERS = [
    "frame",
    "image",
    "x offset",
    "y offset",
    "delay",
    "flipped",
    "audio",
]
_LOOKUP_HEADERS = ["loop", "frame"]


@command("views", "views (animations) operations")
class ViewsCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "input",
            type=Path,
            help="input data file",
        )

        subp = parser.add_subparsers(required=True)
        _JsonCommand().init_parser(subp)
        _InfoCommand().init_parser(subp)
        _ExportCommand().init_parser(subp)
        _LookupCommand().init_parser(subp)


@command("json", "export view data to JSON")
class _JsonCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "-m",
            "--minify",
            help="minify JSON",
            action="store_true",
        )

    def execute(self, args: Namespace) -> None:
        print(_to_json(pin=args.input, minify=args.minify))


@command("info", "print info about a view")
class _InfoCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("view", help="ID or name of the view")

    def execute(self, args: Namespace) -> None:
        pin: Path = args.input
        in_view: str = args.view
        check_datafile(pin)

        in_index: int | None = None
        try:
            in_index = int(in_view)
        except ValueError:
            pass

        gd = read_gamedata(pin)
        if in_index is None:
            in_index = gd.view_names.index(in_view)
        else:
            in_index -= 1
        view = gd.views[in_index]
        name = gd.view_names[in_index]

        print(f'View {in_index + 1} "{name}"')
        print()

        loop_rows: list = []
        for i, loop in enumerate(view.loops):
            loop_rows.append([i + 1, loop.run_next_loop])
        print(tabulate(loop_rows, headers=_LOOP_HEADERS))
        print()

        for i, loop in enumerate(view.loops):
            print(f"Loop {i}:")
            frame_rows: list = []
            for fi, frame in enumerate(loop.frames):
                audio = ""
                if frame.audio_array_id != AUDIO_ARRAY_ID_NONE:
                    audio = gd.audio_clips[frame.audio_array_id].script_name

                frame_rows.append(
                    [
                        fi + 1,
                        frame.image,
                        frame.x_offset,
                        frame.y_offset,
                        frame.delay,
                        frame.flipped,
                        audio,
                    ]
                )
            print(tabulate(frame_rows, headers=_FRAME_HEADERS))
            print()


@command("export", "export views into a file system hierarchy")
class _ExportCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "sprite_dir",
            type=Path,
            help="directory with extracted sprites",
        )
        parser.add_argument(
            "output",
            type=Path,
            help="output directory",
        )

        parser.add_argument(
            "-d",
            "--dirs",
            action="store_true",
            help="group loops into directories instead of using filename prefixes",
        )
        parser.add_argument(
            "-x",
            "--extension",
            help="""
            extension to use when indexing sprites (case-insensitive).
            the index must have been built with the same extension, otherwise things
            may break. delete the index if you are not sure.
            """,
        )
        parser.add_argument(
            "-m",
            "--move",
            action="store_true",
            help="move files instead of copying them",
        )
        parser.add_argument(
            "-t",
            "--threads",
            type=int,
            help="number of threads to use (default is 10)",
            default=10,
        )

        filters_group = parser.add_mutually_exclusive_group()
        filters_group.add_argument(
            "-i",
            "--include",
            help="comma-separated list of ranges to include (e.g 1,4-6,7-9)",
        )
        filters_group.add_argument(
            "-e",
            "--exclude",
            help="comma-separated list of ranges to exclude (e.g. 1,4-6,7-9)",
        )

    def execute(self, args: Namespace) -> None:
        ViewsExporter(
            pin=args.input,
            pout=args.output,
            sprdir=args.sprite_dir,
            include=parse_ranges(args.include),
            exclude=parse_ranges(args.exclude),
            dirs=args.dirs,
            ext=args.extension,
            move=args.move,
            threads=args.threads,
        )


@command("lookup", "lookup views that reference a sprite")
class _LookupCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("sprite", type=int, help="the sprite ID to look up")

    def execute(self, args: Namespace) -> None:
        lookup_sprite(args.input, args.sprite)


def _to_json(pin: Path, minify: bool = True) -> str:
    check_datafile(pin)
    gd = read_gamedata(pin)
    out_json = views_to_json(gd)

    indent = None if minify else 2
    separators = (",", ":") if minify else (",", ": ")
    return json.dumps(out_json, indent=indent, separators=separators)


def views_to_json(gd: GameData) -> list:
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
    def __init__(
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
    ) -> None:
        self.pin = pin
        self.pout = pout
        self.sprdir = sprdir
        self.include = include
        self.exclude = exclude
        self.dirs = dirs
        self.ext = ext
        self.move = move
        self.threads = threads

        check_datafile(self.pin)
        check_dir(self.sprdir)

        if self.ext is not None:
            self.ext = self.ext.removesuffix(".").casefold()

        self.spridx_path = self.sprdir / INDEX_FILE_NAME
        self.index: dict = {}
        self._prepare_index()

        pclib = Clib.read_file(self.pin)
        clib = pclib.clib
        file = clib[GameData.FILENAME]
        with open(self.pin, "rb") as sin:
            sin.seek(pclib.offset + file.offset)
            br = BinaryReader(sin)
            gd = GameData.read(br)
            self.gd = gd
        logger.info("Loaded game data")

        logger.info("Exporting views...")
        fullrange = range(len(gd.views))
        self.indices = filter_ranges(fullrange, self.include, self.exclude)
        ranges = split_range(0, len(gd.views), self.threads)

        start = time.time()
        with concurrent.futures.ThreadPoolExecutor(self.threads) as executor:
            for i, r in enumerate(ranges):
                logger.debug("Started worker thread %d", i)
                executor.submit(self._export_views, r[0], r[1])
        end = time.time()
        logger.info("Done in %.2f seconds", end - start)

    def _export_views(self, start: int, end: int) -> None:
        for i in range(start, end):
            idx = self.indices[i]
            self._export_view(idx)

    def _prepare_index(self) -> None:
        index: dict
        if self.spridx_path.exists():
            logger.info(
                "Found %s, reusing. (Delete to force sprite reindexing.)",
                INDEX_FILE_NAME,
            )
            with open(self.spridx_path, "r", encoding="utf-8") as sin:
                index = json.load(sin)
        else:
            logger.info("Indexing sprites...")
            index = self._build_sprite_index()
            with open(self.spridx_path, "w", encoding="utf-8") as sout:
                json.dump(index, sout)
            logger.info("Index saved to %s", INDEX_FILE_NAME)
        self.index = index

    def _export_view(self, i: int) -> None:
        name = self.gd.view_names[i]
        logger.info('Exporting view %d "%s"', i, name)
        view_dir = self.pout / f"{i + 1}_{name}"
        view = self.gd.views[i]

        os.makedirs(view_dir, exist_ok=True)
        for li, loop in enumerate(view.loops):
            if self.dirs:
                loop_dir = view_dir / str(li)
            else:
                loop_dir = view_dir
            os.makedirs(loop_dir, exist_ok=True)

            for fi, frame in enumerate(loop.frames):
                frame_image = str(frame.image)
                try:
                    src_relpath = self.index[frame_image]
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
    check_datafile(pin)
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

        rows = []
        for li, frames in loops.items():
            if not frames:
                continue
            for fi in frames:
                rows.append([li, fi])
        print(tabulate(rows, headers=_LOOKUP_HEADERS))
        print()
