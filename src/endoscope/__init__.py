import logging
from argparse import ArgumentParser

from endoscope.commands import audio, data, unpack, views


def main() -> None:
    parser = ArgumentParser(
        prog="endoscope",
        description="Datamining tool for Endacopia (and maybe other AGS 3.6.0 games)",
    )
    parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="suppress console output",
    )
    parser.add_argument(
        "-l",
        "--log-level",
        type=str.lower,
        choices=("debug", "info", "warning", "error", "critical"),
        help="logging level",
        default="info",
    )

    subp = parser.add_subparsers(title="commands", required=True)
    unpack.init_parser(subp)
    views.init_parser(subp)
    data.init_parser(subp)
    audio.init_parser(subp)

    args = parser.parse_args()
    logging.basicConfig(
        format="%(message)s",
        level=getattr(logging, args.log_level.upper()),
    )
    logging.root.disabled = args.quiet
    args.func(args)  # pass control to the command


if __name__ == "__main__":
    main()
