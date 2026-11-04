from collections.abc import Callable
from pathlib import Path

from endoscope._internal.utils import check_infile, dump_json
from endoscope.data import utils
from endoscope.data.character import Character
from endoscope.data.gamefile import AudioClip, GameData

sections: dict[str, Callable] = {}


def gamedata_to_json(pin: Path, what: list[str]) -> str:
    check_infile(pin)
    gd = utils.read_gamedata(pin)
    if not what:
        what = list(sections.keys())

    result = {}
    for w in what:
        result[w] = sections[w](gd)

    return dump_json(result)


def _export_chars(gd: GameData) -> list[dict]:
    out: list[dict] = []
    for c in gd.characters:
        cout = _char_to_dict(c)
        out.append(cout)
    return out


def _char_to_dict(c: Character) -> dict:
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


def _export_audio(gd: GameData) -> list[dict]:
    out: list[dict] = []
    for a in gd.audio_clips:
        out.append(_audio_to_dict(a))
    return out


def _audio_to_dict(a: AudioClip) -> dict:
    out: dict = {}
    out["id"] = a.id
    out["scrName"] = a.script_name
    out["repeat"] = a.repeat
    out["fileName"] = a.file_name
    out["fileType"] = a.file_type.name.lower()
    out["priority"] = a.priority
    out["volume"] = a.volume
    return out


def _export_gui_labels(gd: GameData) -> list[dict]:
    out: list[dict] = []
    for l in gd.guis.labels:
        out.append(
            {
                "name": l.control.name,
                "text": l.text,
            }
        )
    return out


def _export_items(gd: GameData) -> list:
    out: list[dict] = []
    for item, name in zip(gd.inventory_items, gd.item_names):
        item_out: dict = {}
        item_out["scrName"] = name
        item_out["image"] = item.image
        item_out["description"] = item.description
        out.append(item_out)
    return out


def _export_dialogue(gd: GameData) -> list:
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


sections["chars"] = _export_chars
sections["audio"] = _export_audio
sections["labels"] = _export_gui_labels
sections["items"] = _export_items
sections["dialogue"] = _export_dialogue


def get_available_sections() -> str:
    return ",".join(sections.keys())
