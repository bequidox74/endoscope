import textwrap
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from tkinter import messagebox as mbox

from endoscope._internal.utils import check_infile, is_program_files
from endoscope.commands import unpack
from endoscope.gui.command_gui import CommandGui


class UnpackWrapper:
    _FILTERS = "* (All files);*.exe (Executable file);*.ags (AGS data file);*.vox (Audio data file)"

    _STATUS_IDLE = "Idle."
    _STATUS_WORKING = "Working..."

    def __init__(self, master) -> None:
        gui = CommandGui(master, "Unpack assets")
        self._gui = gui
        self._future: Future | None = None
        self._executor = ThreadPoolExecutor(1)
        self._unpacker: unpack.AssetUnpacker | None = None

        gui.file(
            "EXE/AGS/VOX file",
            "input",
            UnpackWrapper._FILTERS,
        )
        gui.directory(
            "Output directory",
            "output",
        )
        gui.textinput("Include files\n(leave empty for all)", "include", "*.ogg *.crm")
        gui.textinput("Exclude files", "exclude", "*.ogg *.crm")
        gui.integer("Chunk size (KB)", "chunk", low=1, default=unpack.CHUNK_SIZE_KIB)
        gui.boolean("Dry run (do not modify files)", "dryrun")
        gui.button("Go", self._run)
        gui.button("Stop", self._stop)
        gui.label(UnpackWrapper._STATUS_IDLE, "status")
        gui.run()

    def _run(self) -> None:
        gui = self._gui

        input_: str = gui["input"]
        output: str = gui["output"]

        if not input_:
            _error("No input file provided.")
            return
        pin: Path = Path(input_)
        if not _try(check_infile, pin):
            return

        if not output:
            _error("No output directory provided.")
            return
        pout: Path = Path(output)
        if is_program_files(pout):
            result = mbox.askyesno(
                "Warning",
                textwrap.dedent("""
                You seem to be writing to Program Files, which is usually not what you want!
                Do you want to proceed?
                
                (If this is what you want, make sure to run as administrator.)
                """),
                icon="warning",
            )
            if not result:
                return

        inc: str = gui["include"]
        exc: str = gui["exclude"]

        gui.set_label("status", UnpackWrapper._STATUS_WORKING)
        self._unpacker = unpack.AssetUnpacker(
            pin,
            pout,
            inc.split() if inc else [],
            exc.split() if exc else [],
            int(gui["chunk"]),
            gui["dryrun"],
        )
        self._future = self._executor.submit(self._unpacker.unpack)
        self._future.add_done_callback(self._on_done)

    def _stop(self) -> None:
        if self._unpacker is not None:
            self._unpacker.stop = True
        if self._future is not None:
            self._future.result()

    def _on_done(self, future: Future) -> None:
        try:
            count, elapsed = future.result()
        except ValueError as exc:
            _error(exc.args[0])
            self._future = None
            self._gui.set_label("status", UnpackWrapper._STATUS_IDLE)
            return
        self._gui.root.after(0, self._update_label, count, elapsed)

    def _update_label(self, count: int, elapsed: float) -> None:
        self._gui.set_label(
            "status", f"Extracted {count} assets in {elapsed:.2f} seconds."
        )


def _try[**P, R](func: Callable[P, R], *args: P.args, **kwargs: P.kwargs) -> bool:
    try:
        func(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001
        _error(exc.args[0])
        return False
    return True


def _error(msg: str) -> None:
    mbox.showerror("Error", msg)


def _warn(msg: str) -> None:
    mbox.showwarning("Warning", msg)
