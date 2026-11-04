import logging
import sys
import tkinter as tk

import endoscope
from endoscope.gui.data import DataWrapper
from endoscope.gui.main_menu import MainMenu
from endoscope.gui.rooms import RoomsBitmapsWrapper
from endoscope.gui.sprites import SpritesWrapper
from endoscope.gui.unpack import UnpackWrapper
from endoscope.gui.views import ViewsExportWrapper

logger = logging.getLogger(__name__)


def gui_main() -> None:
    logging.basicConfig(
        format="%(message)s",
        level=logging.DEBUG,
    )
    Gui()


class Gui:
    def __init__(self) -> None:
        self._menu: MainMenu
        self._tk = tk.Tk()
        self._frame = tk.Frame(self._tk)
        self._frame.pack(fill="both", expand=True)

        self._tk.minsize(width=200, height=0)
        self._tk.title(endoscope.FULL_NAME)

        self._tk.withdraw()
        self._make_menu()
        self._center()
        self._tk.deiconify()
        self._tk.mainloop()

        # prevent threads from lingering after the window is closed
        logger.info("Main loop finished, exiting")
        sys.exit(0)

    def _make_menu(self) -> None:
        menu = MainMenu(self._frame)
        self._menu = menu
        menu.add_label(self._tk.wm_title(), centered=True)

        menu.add_button("Unpack assets", self._unpack)
        menu.end_row()

        menu.add_button("Extract sprites", self._sprites)
        menu.end_row()

        menu.add_button("Game data -> JSON", self._data)
        menu.end_row()

        menu.add_button("Room backgrounds", self._room_bitmaps)
        menu.end_row()

        menu.add_button("Export views", self._views_export)
        menu.end_row()

    def _unpack(self) -> None:
        UnpackWrapper(self._frame)

    def _data(self) -> None:
        DataWrapper(self._frame)

    def _sprites(self) -> None:
        SpritesWrapper(self._frame)

    def _room_bitmaps(self) -> None:
        RoomsBitmapsWrapper(self._frame)

    def _views_export(self) -> None:
        ViewsExportWrapper(self._frame)

    def _center(self) -> None:
        self._tk.update_idletasks()
        w = self._tk.winfo_reqwidth()
        h = self._tk.winfo_reqheight()
        x = (self._tk.winfo_screenwidth() - w) // 2
        y = (self._tk.winfo_screenheight() - h) // 2
        self._tk.geometry(f"{w}x{h}+{x}+{y}")


if __name__ == "__main__":
    gui_main()  # support direct launching
