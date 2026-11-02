import logging
import sys
import tkinter as tk

from endoscope.gui.main_menu import MainMenu
from endoscope.gui.unpack import UnpackWrapper

logger = logging.root


def gui_main() -> None:
    Gui()


class Gui:
    def __init__(self) -> None:
        self._menu: MainMenu
        self._tk = tk.Tk()
        self._frame = tk.Frame(self._tk)
        self._frame.pack(fill="both", expand=True)

        self._tk.minsize(width=200, height=0)
        self._tk.title("Endoscope 3.0")

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

        menu.add_button("Extract sprites", lambda: None)
        menu.end_row()

        menu.add_button("Game data -> JSON", lambda: None)
        menu.end_row()

        menu.add_button("Rename audio files", lambda: None)
        menu.end_row()

        menu.add_label("Rooms")
        menu.add_button("Bitmaps", lambda: None)
        menu.add_button("JSON", lambda: None)
        menu.end_row()

        menu.add_label("Views")
        menu.add_button("Export", lambda: None)
        menu.add_button("JSON", lambda: None)
        menu.add_button("Lookup", lambda: None)
        menu.end_row()

    def _unpack(self) -> None:
        UnpackWrapper(self._tk)

    def _center(self) -> None:
        self._tk.update_idletasks()
        w = self._tk.winfo_reqwidth()
        h = self._tk.winfo_reqheight()
        x = (self._tk.winfo_screenwidth() - w) // 2
        y = (self._tk.winfo_screenheight() - h) // 2
        self._tk.geometry(f"{w}x{h}+{x}+{y}")


if __name__ == "__main__":
    gui_main()  # support direct launching
