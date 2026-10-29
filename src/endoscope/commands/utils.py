from pathlib import Path

from endoscope.data.clib import Clib
from endoscope.data.gamefile import GameData
from endoscope.utils import BinaryReader


def read_gamedata(path: Path) -> GameData:
    pclib = Clib.read_file(path)
    clib = pclib.clib
    file = clib[GameData.FILENAME]
    with open(path, "rb") as sin:
        sin.seek(pclib.offset + file.offset)
        br = BinaryReader(sin)
        return GameData.read(br)
