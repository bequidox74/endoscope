from tkinter import messagebox

from endoscope.gui.command_gui import CommandGui


class Wrapper:
    def run(self) -> None:
        pass


class UnpackWrapper:
    _FILTERS = "* (All files);*.exe (Executable file);*.ags (AGS data file);*.vox (Audio data file)"

    _STATUS_IDLE = "Idle."
    _STATUS_WORKING = "Working..."

    def __init__(self, master) -> None:
        gui = CommandGui(master, "Unpack assets")
        self._gui = gui

        gui.file(
            "EXE/AGS/VOX file",
            "input",
            UnpackWrapper._FILTERS,
        )
        gui.directory(
            "Output directory",
            "output",
        )
        gui.button("Go", self._run)
        gui.label(UnpackWrapper._STATUS_IDLE, "status")
        gui.run()

    def _run(self) -> None:
        gui = self._gui
        messagebox.showinfo("Info", f"Extracting {gui["input"]} into {gui["output"]}")
