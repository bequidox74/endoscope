import json
import logging
from argparse import ArgumentParser, Namespace, _SubParsersAction
from pathlib import Path
from typing import Any

from endoscope.data.character import Character
from endoscope.data.gamefile import GameData

from . import utils

logger = logging.getLogger(__name__)


_sections: dict = {}


def _dumps(obj: Any) -> str:
    return json.dumps(obj, indent=2, separators=(",", ": "))


def init_parser(subp: _SubParsersAction) -> None:
    parser: ArgumentParser = subp.add_parser("data")

    parser.add_argument("input", type=Path, help="input data file")
    parser.add_argument(
        "what",
        nargs="*",
        help="what sections to export",
    )

    parser.set_defaults(func=_main)


def _main(args: Namespace) -> None:
    gamedata_to_json(args.input, args.what)


def gamedata_to_json(pin: Path, what: list[str]) -> None:
    gd = utils.read_gamedata(pin)
    if not what:
        what = list(_sections.keys())

    result = {}
    for w in what:
        result[w] = _sections[w](gd)

    print(_dumps(result))


def export_chars(gd: GameData) -> list[dict]:
    out: list[dict] = []
    for c in gd.characters:
        cout = char_to_dict(c)
        out.append(cout)
    return out


def char_to_dict(c: Character) -> dict:
    cout: dict = {}

    cout["name"] = c.name
    cout["scrName"] = c.scr_name
    cout["startingRoom"] = c.starting_room
    cout["walkSpeed"] = c.walk_speed
    cout["walkSpeedY"] = c.walk_speed_y
    cout["baseline"] = c.baseline

    cout["picXOffs"] = c.pic_xoffs
    cout["picYOffs"] = c.pic_yoffs

    cout["view"] = c.view
    cout["idleView"] = c.idle_view
    cout["talkView"] = c.talk_view
    cout["blinkView"] = c.blink_view
    cout["blinkInterval"] = c.blink_interval
    cout["thinkView"] = c.think_view
    cout["defaultView"] = c.default_view
    return cout


_sections["chars"] = export_chars
