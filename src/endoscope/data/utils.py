from pathlib import Path

from endoscope._internal.binary_reader import BinaryReader

from .clib import Clib
from .gamefile import GameData


def read_gamedata(path: Path) -> GameData:
    pclib = Clib.read_file(path)
    clib = pclib.clib
    file = clib[GameData.FILENAME]
    with open(path, "rb") as sin:
        sin.seek(pclib.offset + file.offset)
        br = BinaryReader(sin)
        return GameData.read(br)
