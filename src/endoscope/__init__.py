import logging
import sys
from argparse import ArgumentParser

from endoscope import gui
from endoscope.commands import audio
from endoscope.commands.data import DataCommand
from endoscope.commands.rooms import RoomsCommand
from endoscope.commands.sprites import SpritesCommand
from endoscope.commands.unpack import UnpackCommand
from endoscope.commands.views import ViewsCommand


def main() -> None:
    if len(sys.argv) > 1:
        cli_main()
    else:
        logging.basicConfig(
            format="%(message)s",
            level=logging.DEBUG,
        )
        gui.gui_main()


def cli_main() -> None:
    parser = ArgumentParser(
        prog="endoscope",
        description="Datamining tool for Endacopia (and maybe other AGS 3.6.0 games)",
    )

    log_level = parser.add_mutually_exclusive_group()
    log_level.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="suppress console output",
    )
    log_level.add_argument(
        "-l",
        "--log-level",
        type=str.lower,
        choices=("debug", "info", "warning", "error", "critical"),
        help="logging level",
        default="info",
    )

    parser.add_argument(
        "--profile",
        action="store_true",
        help="profile the program",
    )

    subp = parser.add_subparsers(title="commands", required=True)
    UnpackCommand().init_parser(subp)
    ViewsCommand().init_parser(subp)
    DataCommand().init_parser(subp)
    audio.init_parser(subp)
    SpritesCommand().init_parser(subp)
    RoomsCommand().init_parser(subp)

    args = parser.parse_args()
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, args.log_level.upper()),
    )
    logging.root.disabled = args.quiet

    if args.profile:
        import profiling.tracing

        with profiling.tracing.Profile() as pr:
            args.func(args)
        pr.print_stats()
    else:
        args.func(args)  # pass control to the command


if __name__ == "__main__":
    main()
