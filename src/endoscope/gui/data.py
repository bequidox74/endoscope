import tkinter as tk
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path

from endoscope.commands import data
from endoscope.gui._utils import error
from endoscope.gui.command_gui import CommandGui


class DataWrapper:
    _STATUS_IDLE = "Idle."
    _STATUS_WORKING = "Working..."
    _STATUS_DONE = "Done."

    def __init__(self, master: tk.Misc | None) -> None:
        self._gui: CommandGui
        self._executor = ThreadPoolExecutor(1)
        self._future: Future | None = None

        self._build_gui(master)
        self._gui.run()

    def _build_gui(self, master: tk.Misc | None) -> None:
        gui = CommandGui(master, "Game data to JSON")
        gui.label("Extracts data from game28.dta to a JSON file.", "desc")
        gui.file("EXE/AGS file", "input")
        gui.savefile("Save JSON to", "output", "*.json (JSON file);* (All files)")

        sections = {s.title(): s for s in data.sections}
        gui.checkboxes("Include", sections, True, "include")
        gui.button("Go", self._go)
        gui.label(DataWrapper._STATUS_IDLE, "status")
        self._gui = gui

    def _go(self) -> None:
        if self._future is not None:
            return

        gui = self._gui
        what = [x[1] for x in zip(gui["include"], data.sections) if x[0]]
        if not gui["input"]:
            error("No input file provided.")
            return

        self._future = self._executor.submit(
            data.gamedata_to_json,
            Path(gui["input"]),
            what,
        )
        self._future.add_done_callback(self._on_done)
        gui.set_label("status", DataWrapper._STATUS_WORKING)

    def _on_done(self, future: Future[str]) -> None:
        try:
            sjson = future.result()
            p = Path(self._gui["output"])
            p.write_text(sjson, "utf-8")
            self._gui.set_label("status", DataWrapper._STATUS_DONE)
        except Exception as exc:  # noqa: BLE001
            error(exc.args[0])
            self._gui.set_label("status", DataWrapper._STATUS_IDLE)
        finally:
            self._future = None
