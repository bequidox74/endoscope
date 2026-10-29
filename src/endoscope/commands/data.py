import json
import logging
from argparse import ArgumentParser, Namespace, _SubParsersAction
from pathlib import Path
from typing import Any

from endoscope.data.character import Character
from endoscope.data.gamefile import AudioClip, GameData

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


def export_audio(gd: GameData) -> list[dict]:
    out: list[dict] = []
    for a in gd.audio_clips:
        out.append(audio_to_dict(a))
    return out


def audio_to_dict(a: AudioClip) -> dict:
    out: dict = {}
    out["id"] = a.id
    out["scrName"] = a.script_name
    out["repeat"] = a.repeat
    out["fileName"] = a.file_name
    out["fileType"] = a.file_type.name.lower()
    out["priority"] = a.priority
    out["volume"] = a.volume
    return out


def export_gui_labels(gd: GameData) -> list[dict]:
    out: list[dict] = []
    for l in gd.guis.labels:
        out.append(
            {
                "name": l.control.name,
                "text": l.text,
            }
        )
    return out


def export_items(gd: GameData) -> list:
    out: list[dict] = []
    for item, name in zip(gd.inventory_items, gd.item_names):
        item_out: dict = {}
        item_out["scrName"] = name
        item_out["image"] = item.image
        item_out["description"] = item.description
        out.append(item_out)
    return out


def export_dialogue(gd: GameData) -> list:
    out: list[dict] = []
    for i, (dlg, name) in enumerate(zip(gd.dialogs, gd.dialog_names)):
        dout: dict = {}
        dout["id"] = i
        dout["scrName"] = name
        dout["entryPoints"] = ",".join(str(x) for x in dlg.entry_points)
        dout["startupEntryPoint"] = dlg.startup_entry_point
        dout["options"] = [s for s in dlg.options if s]
        out.append(dout)
    return out


_sections["chars"] = export_chars
_sections["audio"] = export_audio
_sections["labels"] = export_gui_labels
_sections["items"] = export_items
_sections["dialogue"] = export_dialogue
