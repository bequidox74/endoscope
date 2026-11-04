import logging
import shutil
import threading
from pathlib import Path

from endoscope._internal.utils import check_indir, check_infile
from endoscope.data import utils

logger = logging.getLogger(__name__)


class AudioFileRenamer:
    def __init__(self) -> None:
        self.input_path: Path
        self.audio_dir: Path
        self.dry_run: bool
        self.stop_event: threading.Event

        self._fname_index: dict[str, str] = {}

    def rename(
        self,
        input_path: Path,
        audio_dir: Path,
        dry_run: bool,
    ) -> None:
        self.input_path = input_path
        self.audio_dir = audio_dir
        self.dry_run = dry_run
        self.stop_event = threading.Event()

        check_infile(input_path)
        check_indir(audio_dir)

        self._build_index()

        index = self._fname_index
        for p in audio_dir.iterdir():
            if self.stop_event.is_set():
                break
            try:
                name = index[p.name]
            except KeyError:
                continue

            if not dry_run:
                shutil.move(p, p.with_stem(name))

    def _build_index(self) -> None:
        gd = utils.read_gamedata(self.input_path)
        index = {}
        for clip in gd.audio_clips:
            index[clip.file_name] = clip.script_name
        self._fname_index = index
