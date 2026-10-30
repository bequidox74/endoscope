import logging
from argparse import ArgumentParser, Namespace
from datetime import datetime
from pathlib import Path

from endoscope._internal.binary_reader import BinaryReader
from endoscope._internal.utils import check, check_datafile, filter_ranges, parse_ranges
from endoscope.commands.command import Command, command
from endoscope.data.clib import Clib
from endoscope.data.spriteset import Sprite, SpriteIndex, SpriteSet

logger = logging.getLogger(__name__)


@command("sprites")
class SpritesCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        subp = parser.add_subparsers(required=True)
        parser.add_argument("input", type=Path, help="input data file")
        _ExtractCommand().init_parser(subp)


@command("extract")
class _ExtractCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        filters_group = parser.add_mutually_exclusive_group()
        filters_group.add_argument(
            "-i",
            "--include",
            help="comma-separated list or ranges to include (e.g. 1-2,4-7,9)",
        )
        filters_group.add_argument(
            "-e",
            "--exclude",
            help="comma-separated list or ranges to exclude (e.g. 1-2,4-7,9)",
        )

    def execute(self, args: Namespace) -> None:
        extract_sprites(
            pin=args.input,
            include=parse_ranges(args.include),
            exclude=parse_ranges(args.exclude),
        )


def extract_sprites(
    pin: Path,
    include: list[range],
    exclude: list[range],
) -> None:
    check_datafile(pin)
    pclib = Clib.read_file(pin)
    clib = pclib.clib

    sprset_file = clib[SpriteSet.FILENAME]
    spridx_file = clib[SpriteIndex.FILENAME]
    with open(pin, "rb") as sin:
        # read sprite set
        sin.seek(pclib.offset + sprset_file.offset)
        br = BinaryReader(sin)
        sprset = SpriteSet.read(br)
        logger.info("Loaded spriteset data")

        # read index
        sin.seek(pclib.offset + spridx_file.offset)
        spridx = SpriteIndex.read(br)
        logger.info("Loaded sprite index")

    check(sprset.spr_file_id == spridx.spr_file_id, "sprite file ID mismatch")
    ts = datetime.fromtimestamp(sprset.spr_file_id)
    logger.info("Sprite file created at %s", ts)

    logger.debug("Last slot (sprset): %d", sprset.last_slot)
    logger.debug("Last slot (spridx): %d", spridx.last_slot)
    logger.debug("Num sprites (spridx): %d", spridx.count)
    logger.debug("Len (spridx): %d", len(spridx.offsets))
    check(sprset.last_slot == spridx.last_slot, "last slots do not match")
    check(sprset.last_slot == spridx.count - 1, "sprite counts do not match")
    num_sprites = spridx.count

    indices = filter_ranges(range(num_sprites), include, exclude)
    with open(pin, "rb") as sin:
        br = BinaryReader(sin)
        off_sprset = pclib.offset + sprset_file.offset
        for i in indices:
            if i >= num_sprites:
                break  # can't trust that the user will put in adequate numbers.

            off_sprite = off_sprset + spridx.offsets[i]
            sin.seek(off_sprite)

            sprite = Sprite.read_slot(sprset.version, sprset.compression, br)
            if sprite is None:
                continue

            sin.seek(sprite.off_data + 1)
            bitmap = sprite.read_bitmap(br)
