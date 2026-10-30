import logging
import shutil
from argparse import ArgumentParser, Namespace, _SubParsersAction
from pathlib import Path

from endoscope._internal.utils import check_dir, check_exe
from endoscope.data import utils
from endoscope.data.gamefile import GameData

logger = logging.getLogger(__name__)


def init_parser(subp: _SubParsersAction) -> None:
    parser: ArgumentParser = subp.add_parser("audio", help="audio file processing")
    audio_subp = parser.add_subparsers(required=True)
    _init_rename(audio_subp)


def _init_rename(subp: _SubParsersAction) -> None:
    parser: ArgumentParser = subp.add_parser(
        "rename",
        help="renames unpacked audio files in accordance with their script names",
    )

    parser.add_argument("input", type=Path, help="input data file")
    parser.add_argument("audio_dir", type=Path, help="directory containing audio files")

    parser.add_argument(
        "-d",
        "--dry-run",
        action="store_true",
        help="perform a dry run without modifying files",
    )

    parser.set_defaults(func=_main_rename)


def _main_rename(args: Namespace) -> None:
    fp = AudioFileRenamer(args.input, args.audio_dir)
    fp.rename(args.dry_run)


class AudioFileRenamer:
    def __init__(
        self,
        pin: Path,
        audio_dir: Path,
    ) -> None:
        self.pin = pin
        self.audio_dir = audio_dir

    def rename(self, dry_run: bool) -> None:
        pin = self.pin
        paud = self.audio_dir
        check_exe(pin)
        check_dir(paud)

        gd = utils.read_gamedata(pin)
        file_index = self._build_index(gd)

        for p in self.audio_dir.iterdir():
            try:
                name = file_index[p.name]
            except KeyError:
                logger.debug("File did not match: %s", paud.relative_to(p))
                continue

            old_name = p.stem
            if not dry_run:
                shutil.move(p, p.with_stem(name))
                logger.info("Renamed %s to %s", old_name, name)
            else:
                logger.info("Would have renamed %s to %s", old_name, name)

    def _build_index(self, gd: GameData) -> dict[str, str]:
        index = {}
        for clip in gd.audio_clips:
            index[clip.file_name] = clip.script_name
        return index
