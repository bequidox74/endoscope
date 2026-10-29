import json
import logging
from argparse import ArgumentParser, Namespace, _SubParsersAction
from pathlib import Path

from tabulate import tabulate

from endoscope.data.clib import Clib
from endoscope.data.gamefile import GameData
from endoscope.utils import BinaryReader

logger = logging.getLogger(__name__)


AUDIO_ARRAY_ID_NONE = 4294967295


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

    print(f'View {in_index} "{name}"')
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
