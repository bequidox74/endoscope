from argparse import ArgumentParser, Namespace
from pathlib import Path

from endoscope.cli.command import Command, command


@command("sprites", "extract sprites")
class SpritesCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("input", type=Path, help="input data file")
        parser.add_argument("output", type=Path, help="output directory")

        parser.add_argument(
            "-x",
            "--extension",
            help=(
                "extension to save the sprites with "
                "(most should work, but some may lose transparency)"
            ),
            default="png",
        )
        parser.add_argument(
            "-d",
            "--dry-run",
            action="store_true",
            help="perform a dry run without modifying files",
        )
        parser.add_argument(
            "-t",
            "--threads",
            type=int,
            help="number of threads to use for sprite extraction",
            default=10,
        )

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
        raise NotImplementedError
