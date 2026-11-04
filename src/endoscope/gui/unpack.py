from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import ClassVar

from endoscope.commands import unpack
from endoscope.gui._utils import check_program_files, error
from endoscope.gui.command_gui import CommandGui


class UnpackWrapper:
    _FILTERS: ClassVar = ";".join(  # noqa: FLY002
        (
            "* (All files)",
            "*.exe (Executable file)",
            "*.ags (AGS data file)",
            "*.vox (Audio data file)",
        )
    )

    _STATUS_IDLE = "Idle."
    _STATUS_WORKING = "Working..."

    _pin: Path
    _pout: Path
    _inc: list[str]
    _exc: list[str]
    _chunk: int

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
        gui.button("Go", self._run)
        gui.button("Stop", self._stop)
        gui.label(UnpackWrapper._STATUS_IDLE, "status")
        gui.run()

    def _run(self) -> None:
        gui = self._gui

        if not self._validate():
            return

        gui.set_label("status", UnpackWrapper._STATUS_WORKING)
        self._unpacker = unpack.AssetUnpacker()
        self._future = self._executor.submit(
            self._unpacker.unpack,
            self._pin,
            self._pout,
            self._inc,
            self._exc,
            self._chunk,
            dry_run=False,
        )
        self._future.add_done_callback(self._on_done)

    def _validate(self) -> bool:
        gui = self._gui

        input_ = gui["input"]
        output = gui["output"]

        if not input_:
            error("No input file provided.")
            return False
        self._pin: Path = Path(input_)

        if not output:
            error("No output directory provided.")
            return False
        self._pout: Path = Path(output)
        if not check_program_files(self._pout):
            return False

        self._inc = gui["include"]
        self._exc = gui["exclude"]

        try:
            self._chunk = int(gui["chunk"])
            if self._chunk < 0:
                raise ValueError
        except ValueError:
            error("Chunk size must be a positive integer.")
            return False

        return True

    def _stop(self) -> None:
        if self._unpacker is not None:
            self._unpacker.stop = True
        if self._future is not None:
            self._future.result()

    def _on_done(self, future: Future) -> None:
        try:
            count, elapsed = future.result()
        except ValueError as exc:
            error(exc.args[0])
            self._future = None
            self._gui.set_label("status", UnpackWrapper._STATUS_IDLE)
            return
        self._gui.root.after(0, self._update_label, count, elapsed)

    def _update_label(self, count: int, elapsed: float) -> None:
        self._gui.set_label(
            "status", f"Extracted {count} assets in {elapsed:.2f} seconds."
        )
