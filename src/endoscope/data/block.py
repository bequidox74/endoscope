from dataclasses import dataclass
from enum import IntFlag
from typing import ClassVar

from endoscope._internal.binary_reader import BinaryReader


@dataclass
class Block:
    class Flag(IntFlag):
        NUM_ID8 = 0
        NUM_ID32 = 1
        FILE32 = 0
        FILE64 = 2

    LEN_ID: ClassVar = 16

    id: int  # u32/u8
    extid: str | None  # fstr[16]
    size: int  # u64/u32
    off_data: int

    @staticmethod
    def read(br: BinaryReader, flags: int) -> Block:
        blk = Block.__new__(Block)
        start = br.tell()
        blk.id = br.u32() if (flags & Block.Flag.NUM_ID32) else br.u8()
        if blk.id == 0:
            blk.extid = br.fstr(Block.LEN_ID)
        else:
            blk.extid = None
        blk.size = br.u32() if (flags & Block.Flag.FILE32) else br.u64()
        blk.off_data = br.tell() - start
        br.skip(blk.size)
        return blk
