import tkinter as tk
from abc import ABC, abstractmethod
from concurrent.futures import Future, ThreadPoolExecutor
from typing import ClassVar

from endoscope.gui.command_gui import CommandGui


class Wrapper(ABC):
    STATUS_IDLE: ClassVar = "Idle."
    STATUS_WORKING: ClassVar = "Working..."

    can_stop: bool

    def __init__(self, master: tk.Misc | None) -> None:
        self._gui: CommandGui
        self._executor = ThreadPoolExecutor(1)
        self._future: Future | None = None

        gui = self._build_gui(master)
        gui.button("Go", self._go)
        self._gui = gui
        if self.can_stop:
            gui.button("Stop", self._stop)
        gui.label(Wrapper.STATUS_IDLE, "status")
        gui.run()

    @abstractmethod
    def _build_gui(self, master: tk.Misc | None) -> CommandGui:
        pass

    def _go(self) -> None:
        if self._future is not None:
            return
        self._future = self._executor.submit(self.go)

    def go(self) -> None:
        pass

    def _stop(self) -> None:
        pass
