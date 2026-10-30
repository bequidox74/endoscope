import json
import logging
import os
import re
import shutil
from argparse import ArgumentParser, Namespace, _SubParsersAction
from pathlib import Path

from tabulate import tabulate

from endoscope.commands.utils import read_gamedata
from endoscope.data.clib import Clib
from endoscope.data.gamefile import GameData
from endoscope.utils import BinaryReader, check, utils

logger = logging.getLogger(__name__)


AUDIO_ARRAY_ID_NONE = 4294967295  # -1 in two's complement.
INDEX_FILE_NAME = "sprindex.json"


def init_parser(subp: _SubParsersAction) -> None:
    parser: ArgumentParser = subp.add_parser(
        "views",
        help="views (animations) related operations",
    )

    parser.add_argument(
        "input",
        type=Path,
        help="input data file",
    )

    views_subp = parser.add_subparsers(required=True)
    _init_json(views_subp)
    _init_info(views_subp)
    _init_export(views_subp)
    _init_lookup(views_subp)


def _init_json(subp: _SubParsersAction) -> None:
    parser: ArgumentParser = subp.add_parser("json", help="export views as JSON")

    parser.add_argument(
        "-m",
        "--minify",
        help="minify JSON",
        action="store_true",
    )

    parser.set_defaults(func=_main_json)


def _init_info(subp: _SubParsersAction) -> None:
    parser: ArgumentParser = subp.add_parser("info", help="info about view")
    parser.add_argument("view", help="ID or name of the view")
    parser.set_defaults(func=_main_info)


def _init_export(subp: _SubParsersAction) -> None:
    parser: ArgumentParser = subp.add_parser("export", help="export views")

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

    parser.set_defaults(func=_main_export)


def _init_lookup(subp: _SubParsersAction) -> None:
    parser: ArgumentParser = subp.add_parser(
        "lookup",
        help="lookup sprite ID to see what views reference it",
    )

    parser.add_argument("sprite", type=int, help="the sprite ID to look up")

    parser.set_defaults(func=_main_lookup)


def _main_json(args: Namespace) -> None:
    print(to_json(pin=args.input, minify=args.minify))


def to_json(pin: Path, minify: bool = True) -> str:
    pclib = Clib.read_file(pin)
    clib = pclib.clib
    file = clib[GameData.FILENAME]
    with open(pin, "rb") as sin:
        sin.seek(pclib.offset + file.offset)
        br = BinaryReader(sin)
        gd = GameData.read(br)

    out_json = views_to_dict(gd)

    indent = None if minify else 2
    separators = (",", ":") if minify else (",", ": ")
    return json.dumps(out_json, indent=indent, separators=separators)


def views_to_dict(gd: GameData) -> dict:
    out = {}
    for vi, view in enumerate(gd.views):
        view_json: list = []
        out[gd.view_names[vi]] = view_json

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

                if out_frame:
                    frames.append(out_frame)

            view_json.append(out_loop)
    return out


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


def _main_info(args: Namespace) -> None:
    pin: Path = args.input
    in_view: str = args.view

    in_index: int | None = None
    try:
        in_index = int(in_view)
    except ValueError:
        pass

    pclib = Clib.read_file(pin)
    clib = pclib.clib
    file = clib[GameData.FILENAME]
    with open(pin, "rb") as sin:
        sin.seek(pclib.offset + file.offset)
        br = BinaryReader(sin)
        gd = GameData.read(br)

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


def _main_export(args: Namespace) -> None:
    if args.include is not None:
        ranges = utils.parse_ranges(args.include)
    elif args.exclude is not None:
        ranges = utils.parse_ranges(args.exclude)
    else:
        ranges = []

    ve = ViewsExporter(
        args.input,
        args.output,
        args.sprite_dir,
        ranges,
        args.exclude is not None or not ranges,
        args.dirs,
        args.extension,
    )
    ve.export_views()


class ViewsExporter:
    def __init__(
        self,
        pin: Path,
        pout: Path,
        sprdir: Path,
        ranges: list[range],
        exclude: bool,
        dirs: bool,
        ext: str | None,
    ) -> None:
        self.pin = pin
        self.pout = pout
        self.sprdir = sprdir
        self.ranges = ranges
        self.exclude = exclude
        self.dirs = dirs
        self.ext = ext

        if self.ext is not None:
            self.ext = self.ext.removesuffix(".").casefold()

        self.spridx_path = self.sprdir / INDEX_FILE_NAME
        self.index: dict = {}
        self.gd: GameData

    def export_views(self) -> None:
        check(self.sprdir.exists(), "sprite directory does not exist")
        check(self.sprdir.is_dir(), "sprite directory is not a directory")
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

        logger.info("Exporting sprites...")
        if self.exclude:
            indices = filter(
                lambda i: all(i + 1 not in r for r in self.ranges), range(len(gd.views))
            )
            for i in indices:
                self._export_view(i)
        else:
            for r in self.ranges:
                for i in r:
                    self._export_view(i - 1)
        logger.info("Done")

    def _prepare_index(self) -> None:
        index: dict
        if self.spridx_path.exists():
            logger.info(
                "Found %s, reusing. (delete to force sprite reindexing)",
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
        logger.debug('Exporting view %d "%s"', i, name)
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

                out_name = f"{fi + 1}{suffix}"
                if not self.dirs:
                    out_name = f"{li + 1}_{out_name}"

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
                    f"duplicate files: {relpath} and {out[n]}. Prefix duplicates with '_' to ignore them."
                )
            out[n] = relpath

        return out


def _main_lookup(args: Namespace) -> None:
    lookup_sprite(args.input, args.sprite)


_LOOKUP_HEADERS = ["loop", "frame"]


def lookup_sprite(pin: Path, sid: int) -> None:
    gd = read_gamedata(pin)

    refs: dict[int, dict[int, list[int]]] = {}
    for vi, view in enumerate(gd.views):
        for loops, loop in enumerate(view.loops):
            for fi, frame in enumerate(loop.frames):
                if frame.image == sid:
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
