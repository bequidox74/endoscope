from argparse import ArgumentParser, Namespace
from pathlib import Path

from endoscope.commands.audio import AudioFileRenamer

from .command import Command, command


@command("audio", "rename unpacked audio to match internal names")
class AudioCommand(Command):
    def _init_parser(self, parser: ArgumentParser) -> None:
        parser.add_argument(
            "input",
            type=Path,
            help="input data file",
        )
        parser.add_argument(
            "audio_dir",
            type=Path,
            help="directory containing audio files",
        )

        parser.add_argument(
            "-d",
            "--dry-run",
            action="store_true",
            help="perform a dry run without modifying files",
        )

    def execute(self, args: Namespace) -> None:
        AudioFileRenamer().rename(args.input, args.audio_dir, args.dry_run)
