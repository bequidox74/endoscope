import textwrap
import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from endoscope.commands.rooms import BitmapExtractor
from endoscope.gui._utils import error
from endoscope.gui.command_gui import CommandGui


class RoomsBitmapsWrapper:
    _EXTENSIONS = ("png", "jpg", "tiff", "tga", "bmp", "avif", "gif", "ico", "webp")

    def __init__(self, master: tk.Misc | None) -> None:
        self._gui: CommandGui

        self._executor = ThreadPoolExecutor(1)
        self._future: Future | None = None
        self._extractor: BitmapExtractor | None = None

        self._build_gui(master)
        self._gui.run()

    def _build_gui(self, master: tk.Misc | None) -> None:
        gui = CommandGui(master, "Room bitmaps")
        gui.label(
            textwrap.dedent("""
            Extracts room backgrounds and masks as bitmaps.
            Needs unpacked room (.crm) files first (use "Unpack assets").
            """).strip(),
            "desc",
        )
        gui.directory("Directory with CRM files", "input")
        gui.directory("Output directory", "output")
        gui.boolean("Use threads (faster)", "threads", True)
        gui.textinput("Room file pattern", "glob", "*.crm")

        exts = {e.upper(): e for e in RoomsBitmapsWrapper._EXTENSIONS}
        gui.combo("Extension", exts, "extension")

        gui.button("Go", self._go)
        gui.button("Stop", self._stop)
        gui.label("Idle.", "status")
        self._gui = gui

    def _go(self) -> None:
        if self._future is not None:
            return

        gui = self._gui
        pin = Path(gui["input"])
        pout = Path(gui["output"])
        glob = gui["glob"]
        if not glob:
            glob = "*.crm"
        extension = gui["extension"]
        threads = 10 if bool(gui["threads"]) else 1

        self._extractor = BitmapExtractor()
        self._future = self._executor.submit(
            self._extractor.extract,
            pin,
            pout,
            threads,
            False,
            glob,
            extension,
        )
        self._future.add_done_callback(self._on_done)
        gui.set_label("status", "Working...")

    def _stop(self) -> None:
        if self._extractor is None:
            return
        self._extractor.stop = True

    def _on_done(self, future: Future[tuple[int, float]]) -> None:
        try:
            count, elapsed = future.result()
            self._gui.set_label(
                "status",
                f"Processed {count} rooms in {elapsed:.2f} seconds.",
            )
        except Exception as exc:  # noqa: BLE001
            error(exc.args[0])
            self._gui.set_label("status", "Idle.")
        finally:
            self._future = None
