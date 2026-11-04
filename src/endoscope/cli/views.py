from argparse import ArgumentParser, Namespace
from pathlib import Path

from .command import Command, command


@command("views", "views (animations) operations")
class ViewsCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "input",
            type=Path,
            help="input data file",
        )

        subp = parser.add_subparsers(required=True)
        _JsonCommand().init_parser(subp)
        _InfoCommand().init_parser(subp)
        _ExportCommand().init_parser(subp)
        _LookupCommand().init_parser(subp)


@command("json", "export view data to JSON")
class _JsonCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "-m",
            "--minify",
            help="minify JSON",
            action="store_true",
        )

    def execute(self, args: Namespace) -> None:
        raise NotImplementedError


@command("info", "print info about a view")
class _InfoCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("view", help="ID or name of the view")

    def execute(self, args: Namespace) -> None:
        raise NotImplementedError


@command("export", "export views into a file system hierarchy")
class _ExportCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "sprite_dir",
            type=Path,
            help="directory with extracted sprites",
        )
        parser.add_argument(
            "output",
            type=Path,
            help="output directory",
        )

        parser.add_argument(
            "-d",
            "--dirs",
            action="store_true",
            help="group loops into directories instead of using filename prefixes",
        )
        parser.add_argument(
            "-x",
            "--extension",
            help="""
            extension to use when indexing sprites (case-insensitive).
            the index must have been built with the same extension, otherwise things
            may break. delete the index if you are not sure.
            """,
        )
        parser.add_argument(
            "-m",
            "--move",
            action="store_true",
            help="move files instead of copying them",
        )
        parser.add_argument(
            "-t",
            "--threads",
            type=int,
            help="number of threads to use (default is 10)",
            default=10,
        )

        filters_group = parser.add_mutually_exclusive_group()
        filters_group.add_argument(
            "-i",
            "--include",
            help="comma-separated list of ranges to include (e.g 1,4-6,7-9)",
        )
        filters_group.add_argument(
            "-e",
            "--exclude",
            help="comma-separated list of ranges to exclude (e.g. 1,4-6,7-9)",
        )

    def execute(self, args: Namespace) -> None:
        raise NotImplementedError


@command("lookup", "lookup views that reference a sprite")
class _LookupCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("sprite", type=int, help="the sprite ID to look up")

    def execute(self, args: Namespace) -> None:
        raise NotImplementedError
