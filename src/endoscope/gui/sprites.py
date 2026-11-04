import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from endoscope._internal.utils import parse_ranges
from endoscope.commands.sprites import SpriteExtractor
from endoscope.gui._utils import error
from endoscope.gui.command_gui import CommandGui


class SpritesWrapper:
    _EXTENSIONS = ("png", "jpg", "tiff", "tga", "bmp", "avif", "gif", "ico", "webp")

    def __init__(self, master: tk.Misc | None) -> None:
        self._gui = self._build_gui(master)
        self._gui.run()

        self._executor = ThreadPoolExecutor(1)
        self._future: Future | None = None
        self._extractor: SpriteExtractor | None = None

    def _build_gui(self, master: tk.Misc | None) -> CommandGui:
        gui = CommandGui(master, "Extract sprites")
        gui.label("Extract sprites from the game into a directory.", "desc")
        gui.file("EXE/AGS file", "input")
        gui.directory("Output directory", "output")
        gui.boolean("Use threads (faster)", "threads", True)
        gui.textinput("Include ranges\n(leave empty for all)", "include", "1-5,6,9-13")
        gui.textinput("Exclude ranges", "exclude", "1-5,6,9-13")

        exts = {e.upper(): e for e in SpritesWrapper._EXTENSIONS}
        gui.combo("Extension", exts, "extension")

        gui.button("Go", self._go)
        gui.button("Stop", self._stop)
        gui.label("Idle.", "status")
        return gui

    def _go(self) -> None:
        if self._future is not None:
            return

        gui = self._gui
        pin = Path(gui["input"])
        pout = Path(gui["output"])
        include = parse_ranges(gui["include"])
        exclude = parse_ranges(gui["exclude"])
        extension = gui["extension"]
        threads = SpriteExtractor.DEFAULT_THREADS if bool(gui["threads"]) else 1

        self._extractor = SpriteExtractor()
        self._future = self._executor.submit(
            self._extractor.extract,
            pin,
            pout,
            include,
            exclude,
            False,
            extension,
            threads,
        )
        self._future.add_done_callback(self._on_done)
        gui.set_label("status", "Working...")

    def _stop(self) -> None:
        if self._extractor is None:
            return
        self._extractor.stop.set()

    def _on_done(self, future: Future[tuple[int, float]]) -> None:
        try:
            count, elapsed = future.result()
            self._gui.set_label(
                "status",
                f"Extracted {count} sprites in {elapsed:.2f} seconds.",
            )
        except Exception as exc:  # noqa: BLE001
            error(exc.args[0])
            self._gui.set_label("status", "Error.")
        finally:
            self._future = None
