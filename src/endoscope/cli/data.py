from argparse import ArgumentParser, Namespace
from pathlib import Path

from endoscope.commands.data import gamedata_to_json, sections

from .command import Command, command


@command("data", "extract data from game28.dta to JSON")
class DataCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument("input", type=Path, help="input data file")
        parser.add_argument(
            "what",
            nargs="*",
            help=f"what sections to export ({", ".join(sections)})",
        )

    def execute(self, args: Namespace) -> None:
        print(gamedata_to_json(args.path, args.what))
