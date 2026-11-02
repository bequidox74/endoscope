import textwrap
import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from endoscope._internal.utils import parse_ranges
from endoscope.commands.views import ViewsExporter
from endoscope.gui._utils import error
from endoscope.gui.command_gui import CommandGui


class ViewsExportWrapper:
    _EXTENSIONS = ("png", "jpg", "tiff", "tga", "bmp", "avif", "gif", "ico", "webp")

    def __init__(self, master: tk.Misc | None) -> None:
        self._gui: CommandGui

        self._executor = ThreadPoolExecutor(1)
        self._future: Future | None = None
        self._extractor: ViewsExporter | None = None

        self._build_gui(master)
        self._gui.run()

    def _build_gui(self, master: tk.Misc | None) -> None:
        gui = CommandGui(master, "Room bitmaps")
        gui.label(
            textwrap.dedent("""
            Reads AGS view (animation) data and sorts them into directories, copying sprites.
            Needs extracted sprites to function (use "Extract sprites").
            """).strip(),
            "desc",
        )
        gui.file("EXE/AGS file", "input")
        gui.directory("Output directory", "output")
        gui.directory("Directory with sprites", "sprdir")

        gui.textinput("Include ranges\n(leave empty for all)", "include", "1-5,6,9-13")
        gui.textinput("Exclude ranges", "exclude", "1-5,6,9-13")

        exts = {e.upper(): e for e in ViewsExportWrapper._EXTENSIONS}
        gui.combo("Extension", exts, "extension")

        gui.combo("Action", {"Copy": "copy", "Move": "move"}, "action")
        gui.boolean("Use threads (faster)", "threads", True)

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
        sprdir = Path(gui["sprdir"])
        include = parse_ranges(gui["include"])
        exclude = parse_ranges(gui["exclude"])
        extension = gui["extension"]
        move = gui["action"] == "move"
        threads = 10 if bool(gui["threads"]) else 1

        self._extractor = ViewsExporter()
        self._future = self._executor.submit(
            self._extractor.extract,
            pin,
            pout,
            sprdir,
            include,
            exclude,
            True,
            extension,
            move,
            threads,
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
                f"Exported {count} views in {elapsed:.2f} seconds.",
            )
        except Exception as exc:  # noqa: BLE001
            error(exc.args[0])
            self._gui.set_label("status", "Idle.")
        finally:
            self._future = None
