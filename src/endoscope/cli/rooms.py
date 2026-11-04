from argparse import ArgumentParser, Namespace
from pathlib import Path

from endoscope.commands.rooms import BitmapExtractor, JsonExporter

from .command import Command, command


@command("rooms", "room-related operations")
class RoomsCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        subp = parser.add_subparsers(required=True)
        parser.add_argument(
            "roomdir",
            type=Path,
            help="directory with room (.crm) files",
        )
        _BitmapsCommand().init_parser(subp)
        _JsonCommand().init_parser(subp)


@command("bitmaps", "extract room backgrounds and masks")
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
        BitmapExtractor().extract(
            args.roomdir,
            args.output,
            args.threads,
            args.dry_run,
            args.glob,
            args.extension,
        )


@command("json", "export room data to JSON")
class _JsonCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "-o",
            "--output",
            type=Path,
            nargs="?",
            help="output path",
        )
        parser.add_argument(
            "-g",
            "--glob",
            help="file name glob pattern (e.g. *.crm)",
            default="*.crm",
        )
        parser.add_argument(
            "-m",
            "--minify",
            action="store_true",
            help="minify resulting JSON",
        )

    def execute(self, args: Namespace) -> None:
        JsonExporter(
            args.output,
            args.roomdir,
            args.glob,
            args.minify,
        )
