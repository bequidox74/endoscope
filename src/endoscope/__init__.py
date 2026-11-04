import sys

from endoscope import cli, gui

NAME = "Endoscope"
VERSION = "3.1"
FULL_NAME = f"{NAME} {VERSION}"


def main() -> None:
    if len(sys.argv) > 1:
        cli.cli_main()
    else:
        gui.gui_main()


if __name__ == "__main__":
    main()
