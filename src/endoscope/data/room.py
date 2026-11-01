# See Common/game/room_file.cpp
from dataclasses import dataclass
from enum import IntEnum
from typing import ClassVar

from endoscope._internal.binary_reader import BinaryReader
from endoscope.data import encrypt
from endoscope.data.block import Block

### Constants ###
MIN_ROOM_HOTSPOTS = 20
LEGACY_HOTSPOT_NAME_LEN = 30
LEGACY_ROOM_PASSWORD_LENGTH = 11
LEGACY_ROOM_PASSWORD_SALT = 60
ROOM_MESSAGE_FLAG_DISPLAYNEXT = 200
MAX_WALK_AREAS = 15
MAX_WALK_BEHINDS = 16
MAX_ROOM_REGIONS = 16
MAX_MESSAGES = 100


@dataclass
class Hotspot:
    walkto_x: int  # i16
    walkto_y: int  # i16
    name: str  # pstr
    scr_name: str  # pstr
    events: list[str]

    @staticmethod
    def read(br: BinaryReader) -> Hotspot:
        return Hotspot(
            walkto_x=br.i16(),
            walkto_y=br.i16(),
            name="",
            scr_name="",
            events=[],
        )


@dataclass
class Object:
    sprite: int  # i16
    x: int  # i16
    y: int  # i16
    room: int  # i16
    on: bool  # i16
    baseline: int
    flags: int
    events: list[str]

    @staticmethod
    def read(br: BinaryReader) -> Object:
        return Object(
            sprite=br.i16(),
            x=br.i16(),
            y=br.i16(),
            room=br.i16(),
            on=bool(br.i16()),
            baseline=0,
            flags=0,
            events=[],
        )


@dataclass
class WalkArea:
    scaling_far: int  # i16
    player_view: int  # i16
    scaling_near: int  # i16
    top: int  # i16
    bottom: int  # i16

    @staticmethod
    def read(br: BinaryReader) -> WalkArea:
        return WalkArea(
            scaling_far=br.i16(),
            player_view=br.i16(),
            scaling_near=br.i16(),
            top=br.i16(),
            bottom=br.i16(),
        )


@dataclass
class Message:
    displayas: int  # i8
    flags: int  # i8
    cstr: str  # cstr


@dataclass
class Region:
    light: int  # i16
    tint: int  # i32
    events: list[str]


@dataclass
class Room:
    class BlockType(IntEnum):
        NONE = 0
        MAIN = 1
        SCRIPT = 2
        COMPSCR = 3
        COMPSCR2 = 4
        OBJNAMES = 5
        ANIMBG = 6
        COMPSCR3 = 7
        PROPERTIES = 8
        OBJECT_SC_NAMES = 9
        EOF = 0xFF

    ROOM_BLOCK_FLAGS: ClassVar = Block.Flag.NUM_ID8 | Block.Flag.FILE64
    SUFFIX: ClassVar = ".crm"

    blocks: dict[Room.BlockType | str, tuple[Block, int]]  # (block, offset)

    ### Header ###
    version: int  # i16

    ### Main block ###
    bg_bpp: int  # i32
    walkbehind_baselines: list[int]  # i16[i16]
    hotspots: list[Hotspot]  # [#i32]
    # i32 unused
    edge_top: int  # i16
    edge_bottom: int  # i16
    edge_left: int  # i16
    edge_right: int  # i16
    objects: list[Object]  # [i16]
    # i32 unused
    num_regions: int  # i32
    room_events: list[str]  # cstr[u32]
    hotspot_events: list[str]  # cstr[u32]
    object_events: list[str]  # cstr[u32]
    region_events: list[str]  # cstr[u32]
    # obj_baselines: list[int]  # i32[len(objects)]
    width: int  # i16
    height: int  # i16
    object_flags: list[int]  # i16[len(objects)]
    mask_res: int  # i16
    walkareas: list[WalkArea]  # [MAX_WALK_AREAS]
    # 0 x11
    startup_music: int  # u8
    saveload_disabled: bool  # u8
    playerchar_off: bool  # u8
    player_view: int  # u8
    music_volume: int  # u8
    flags: int  # i8
    # reserved 0 x4
    # num_messages: int  # i16
    gameid: int  # u32
    messages: list[Message]  # [num_messages]
    # i16 unused
    # WA.PlayerView (skip)
    regions: list[Region]  # [num_regions]
    off_bitmaps: int

    @staticmethod
    def read(br: BinaryReader) -> Room:
        rm = Room.__new__(Room)
        start = br.tell()  # of room into file
        rm.version = br.u16()

        rm.blocks = {}
        while True:
            off_blk = br.tell() - start
            blk = Block.read(br, Room.ROOM_BLOCK_FLAGS)

            blkid = (
                Room.BlockType(blk.id) if blk.id != Room.BlockType.NONE else blk.extid
            )
            assert blkid is not None
            rm.blocks[blkid] = (blk, off_blk)

            br.seek(start + off_blk + blk.off_data)
            if blk.id == Room.BlockType.MAIN:
                Room._read_main(rm, br, off_blk)
            elif blk.id == Room.BlockType.EOF:
                break
            else:
                break
                # raise NotImplementedError

        return rm

    @staticmethod
    def _read_main(rm: Room, br: BinaryReader, offset: int) -> None:
        rm.bg_bpp = br.u32()
        rm.walkbehind_baselines = [br.i16() for _ in range(br.i16())]

        rm.hotspots = [Hotspot.read(br) for _ in range(br.i32())]
        num_hs = len(rm.hotspots)
        hs_names = [br.pstr() for _ in range(num_hs)]
        hs_scr_names = [br.pstr() for _ in range(num_hs)]
        for i, h in enumerate(rm.hotspots):
            h.name = hs_names[i]
            h.scr_name = hs_scr_names[i]

        br.i32()  # unused
        rm.edge_top = br.i16()
        rm.edge_bottom = br.i16()
        rm.edge_left = br.i16()
        rm.edge_right = br.i16()
        rm.objects = [Object.read(br) for _ in range(br.i16())]
        br.i32()  # unused
        rm.num_regions = br.i32()

        rm.room_events = [br.cstr() for _ in range(br.i32())]
        for h in rm.hotspots:
            h.events = [br.cstr() for _ in range(br.i32())]
        for o in rm.objects:
            o.events = [br.cstr() for _ in range(br.i32())]
        region_events: list[list[str]] = []
        for _ in range(rm.num_regions):
            region_events.append([br.cstr() for _ in range(br.i32())])

        obj_baselines = [br.i32() for _ in range(len(rm.objects))]
        rm.width = br.i16()
        rm.height = br.i16()
        obj_flags = [br.i16() for _ in range(len(rm.objects))]
        for i, o in enumerate(rm.objects):
            o.baseline = obj_baselines[i]
            o.flags = obj_flags[i]

        rm.mask_res = br.i16()
        br.i32()  # unused
        rm.walkareas = [WalkArea.read(br) for _ in range(MAX_WALK_AREAS + 1)]
        br.skip(11)  # unused
        rm.startup_music = br.u8()
        rm.saveload_disabled = bool(br.u8())
        rm.playerchar_off = bool(br.u8())
        rm.player_view = br.u8()
        rm.music_volume = br.u8()
        rm.flags = br.u8()
        br.skip(4)  # reserved
        num_messages = br.i16()
        rm.gameid = br.u32()

        rm.messages = [Message(br.u8(), br.u8(), "") for _ in range(num_messages)]
        for m in rm.messages:
            m.cstr = encrypt.decrypt(br.read(br.u32()))

        br.i16()  # unused
        for _ in range(MAX_WALK_AREAS + 1):
            br.i16()  # skip duplicate walk areas

        rm.regions = []
        rlights = [br.u16() for _ in range(MAX_ROOM_REGIONS)]
        rtints = [br.u32() for _ in range(MAX_ROOM_REGIONS)]
        for i in range(rm.num_regions):
            rm.regions.append(Region(rlights[i], rtints[i], region_events[i]))

        rm.off_bitmaps = br.tell() - offset
