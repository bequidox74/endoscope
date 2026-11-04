from argparse import ArgumentParser, Namespace
from pathlib import Path

from .command import Command, command


@command("unpack", "unpack game assets")
class UnpackCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "input",
            type=Path,
            help="input file (.exe, .ags, .vox)",
        )
        parser.add_argument(
            "output",
            type=Path,
            help="output directory (will be created if needed)",
        )

        parser.add_argument(
            "-c",
            "--chunk-size",
            default=64,
            type=int,
            help="chunk size in KiB for copying (default is 64)",
        )
        parser.add_argument(
            "-d",
            "--dry-run",
            action="store_true",
            help="do a dry run without writing any files (effectively lists assets)",
        )

        filters = parser.add_mutually_exclusive_group()
        filters.add_argument(
            "-i",
            "--include",
            nargs="+",
            help="wildcards for included files (can have multiple)",
        )
        filters.add_argument(
            "-e",
            "--exclude",
            nargs="+",
            help="wildcards for excluded files (can have multiple)",
        )

    def execute(self, args: Namespace) -> None:
        raise NotImplementedError
