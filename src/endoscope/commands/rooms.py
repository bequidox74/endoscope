import itertools
import logging
import os
import time
from argparse import ArgumentParser, Namespace
from collections.abc import Iterable
from concurrent.futures import ThreadPoolExecutor
from fnmatch import fnmatch
from pathlib import Path

from PIL import Image

from endoscope._internal.reader import BinaryReader
from endoscope._internal.utils import check, check_dir
from endoscope.commands.command import Command, command
from endoscope.data import decode
from endoscope.data.room import Room

logger = logging.root


@command("rooms", "room operations")
class RoomsCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "roomdir",
            type=Path,
            help="directory with room (.crm) files",
        )
        subp = parser.add_subparsers(required=True)
        _BitmapsCommand().init_parser(subp)


@command("bitmaps", "extract room bitmaps")
class _BitmapsCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("output", type=Path, help="output directory")

        parser.add_argument(
            "-t",
            "--threads",
            type=int,
            help="number of threads to use (default: 3)",
            default=3,
        )
        parser.add_argument(
            "-d",
            "--dry-run",
            action="store_true",
            help="perform a dry run without creating files",
        )
        parser.add_argument(
            "-g",
            "--glob",
            help="file name glob pattern (e.g. *.crm)",
            default="*.crm",
        )
        parser.add_argument(
            "-x",
            "--extension",
            help="extension to save the files with (e.g. png, jpg, tga, tiff, etc.)",
            default="png",
        )

    def execute(self, args: Namespace) -> None:
        BitmapExtractor(
            args.roomdir,
            args.output,
            args.threads,
            args.dry_run,
            args.glob,
            args.extension,
        )


class BitmapExtractor:
    def __init__(
        self,
        roomdir: Path,
        pout: Path,
        nthreads: int,
        dry_run: bool,
        glob: str,
        extension: str,
    ) -> None:
        self.roomdir = roomdir
        self.pout = pout
        self.nthreads = nthreads
        self.dry_run = dry_run
        self.glob = glob
        self.extension = extension

        check_dir(roomdir)
        os.makedirs(pout, exist_ok=True)

        room_files: list[Path] = []
        for p in roomdir.iterdir():
            if not fnmatch(p.name, glob):
                continue  # skip masked files
            room_files.append(p)
        logger.debug("Found %d matching files", len(room_files))
        if not room_files:
            logger.info("No files to process, exiting")

        self.openfiles: set[Path] = set()
        start = time.time()
        with ThreadPoolExecutor(nthreads) as executor:
            bsize = len(room_files) // nthreads
            if bsize == 0:
                bsize = 1
            for batch in itertools.batched(room_files, bsize):
                executor.submit(self._process_batch, batch)
        end = time.time()
        logger.info(
            "Done processing %d rooms in %.2f seconds",
            len(room_files),
            end - start,
        )

    def _process_batch(self, batch: Iterable[Path]) -> None:
        for p in batch:
            logger.debug("Processing room %s", p.name)
            if p in self.openfiles:
                raise RuntimeError
            with open(p, "rb") as sin:
                try:
                    br = BinaryReader(sin)
                    room = Room.read(br)
                    self._extract(p.stem, br, room)
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    logger.exception(
                        "Error while processing room %s", p.name, exc_info=exc
                    )

    def _extract(self, name: str, br: BinaryReader, rm: Room) -> None:
        base_path = self.pout / f"{name}/"
        ext = self.extension

        ### Primary BG ###
        mainblk = rm.blocks[Room.BlockID.MAIN]
        bmoffset = mainblk[1] + rm.off_bitmaps
        br.seek(bmoffset)

        bitmap = self._read_lzw(br)

        out_path = base_path / f"bg_0.{ext}"
        self._save_bitmap(out_path, rm.width, rm.height, bitmap, True)

        ### Masks ###
        self._extract_mask(base_path / f"regions.{ext}", br)
        self._extract_mask(base_path / f"walkareas.{ext}", br)
        self._extract_mask(base_path / f"walkbehinds.{ext}", br)
        self._extract_mask(base_path / f"hotspots.{ext}", br)

        ### Secondary BGs ###
        try:
            bgblk = rm.blocks[Room.BlockID.ANIMBG]
        except KeyError:
            return  # no secondary BGs
        br.seek(bgblk[1] + bgblk[0].off_data)
        nframes = br.u8()
        br.u8()  # animation speed

        _ = [bool(br.u8()) for _ in range(nframes)]  # palette sharing; unused
        for i in range(nframes - 1):
            out_path = base_path / f"bg_{i + 1}.{self.extension}"
            bitmap = self._read_lzw(br)
            self._save_bitmap(out_path, rm.width, rm.height, bitmap, True)

    def _read_lzw(self, br: BinaryReader) -> bytes:
        br.skip(256 * 4)  # palette
        origsize = br.u32()
        compsize = br.u32()
        raw = br.read(compsize)
        ok, decomp = decode.lzw(raw, origsize)
        check(ok, "LZW decompression failed")
        decomp = decomp[8:]
        return decode.sequential_rgba(decomp)

    def _extract_mask(self, pout: Path, br: BinaryReader) -> None:
        w = br.u16()
        h = br.u16()
        try:
            decomp, read = decode.rle_online(1, w * h, br)
            palette = decode.PALETTE256
            br.skip(3 * 256)
            if read != 0:
                bitmap = decode.indexed_rgb(decomp, palette)
                self._save_bitmap(pout, w, h, bitmap, False)
        except ValueError as exc:
            logger.exception("Unable to extract mask %s", pout, exc_info=exc)

    def _save_bitmap(self, out_path: Path, w: int, h: int, bitmap: bytes, rgba: bool) -> None:
        if self.dry_run:
            return
        os.makedirs(out_path.parent, exist_ok=True)

        fmt = "RGBA" if rgba else "RGB"
        img = Image.frombuffer(fmt, (w, h), bitmap)
        if rgba:
            img = img.convert("RGB")

        try:
            img.save(out_path)
            logger.debug("Saved %s", out_path)
        except ValueError as exc:
            logger.exception("Unable to save %s", out_path, exc_info=exc)
