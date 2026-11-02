import tkinter as tk
from collections.abc import Callable
from tkinter import ttk


class MainMenu:
    def __init__(self, master: tk.Misc) -> None:
        self.master = master

        self._frame = ttk.Frame(master, padding=8)
        self._frame.pack(fill="x")

        self._row: ttk.Frame | None = None

    def _get_row(self) -> ttk.Frame:
        if self._row is None:
            self._row = ttk.Frame(self._frame)
            self._row.pack(fill="x")

        return self._row

    def end_row(self) -> None:
        self._row = None

    def add_button(self, text: str, handler: Callable[[], None]) -> None:
        btn = ttk.Button(self._get_row(), text=text, command=handler)
        btn.pack(side="left", fill="x", expand=True, padx=2, pady=2)

    def add_label(self, text: str, centered: bool = True) -> None:
        if self._row is not None and self._row.winfo_children():
            self.end_row()

        lbl = ttk.Label(
            self._get_row(), text=text, anchor="center" if centered else "w"
        )
        lbl.pack(fill="x", padx=1, pady=1)

        self.end_row()
