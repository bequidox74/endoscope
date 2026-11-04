import tkinter as tk
from collections.abc import Callable
from tkinter import filedialog, ttk
from typing import Any


def _parse_filters(filters: str | None) -> list[tuple[str, str]]:
    if not filters:
        return [("All files", "*")]
    types: list[tuple[str, str]] = []
    for part in filters.split(";"):
        part = part.strip()
        if not part:
            continue
        pattern, _, desc = part.partition(" ")
        types.append((desc.strip().strip("()") or pattern, pattern))
    return types


type Choices = dict[str, str]


class _HintEntry(ttk.Entry):
    def __init__(self, master, hint="", **kw) -> None:
        super().__init__(master, **kw)
        self.hint = hint
        self._showing = False
        self.bind("<FocusIn>", self._hide)
        self.bind("<FocusOut>", self._show)
        self._show()

    def _show(self, _event=None) -> None:
        if self.hint and not super().get():
            self.insert(0, self.hint)
            self.configure(foreground="gray")
            self._showing = True

    def _hide(self, _event=None) -> None:
        if self._showing:
            self.delete(0, "end")
            self.configure(foreground="")
            self._showing = False

    def get(self) -> str:
        return "" if self._showing else super().get()


class CommandGui:
    def __init__(self, master, title="Command", padding=12) -> None:
        self.master = master
        self.root = tk.Toplevel(master)

        self.root.withdraw()
        self.root.title(title)
        ttk.Style(self.root).layout(
            "Bare.TCheckbutton",
            [
                (
                    "Checkbutton.padding",
                    {
                        "sticky": "nswe",
                        "children": [
                            ("Checkbutton.indicator", {"side": "left", "sticky": ""}),
                        ],
                    },
                ),
            ],
        )
        self._frame = ttk.Frame(self.root, padding=padding)
        self._frame.pack(fill="both", expand=True)
        self._frame.columnconfigure(1, weight=1)
        self._row = 0
        self._getters = {}
        self._button_row = None
        self._labels: dict[str, ttk.Label] = {}

    def center(self) -> None:
        self.master.update_idletasks()
        self.root.update_idletasks()
        width = self.root.winfo_reqwidth()
        height = self.root.winfo_reqheight()

        x = self.master.winfo_rootx() + (self.master.winfo_width() - width) // 2
        y = self.master.winfo_rooty() + (self.master.winfo_height() - height) // 2

        self.root.geometry(f"+{x}+{y}")

    def _add_row(
        self,
        label: str,
        vid: str | None,
        getter_factory: Callable[[tk.Widget], Any],
        top_align: bool = False,
    ) -> None:
        self._button_row = None
        key = vid or label
        if key in self._getters:
            raise ValueError(f"Duplicate id: {key!r}")
        ttk.Label(self._frame, text=label).grid(
            row=self._row,
            column=0,
            sticky="nw" if top_align else "w",
            padx=(0, 10),
            pady=3,
        )
        ctrl = ttk.Frame(self._frame)
        ctrl.grid(row=self._row, column=1, sticky="ew", pady=3)
        self._getters[key] = getter_factory(ctrl)
        self._row += 1

    def label(self, text: str, lid: str | None = None) -> None:
        self._button_row = None
        l = ttk.Label(self._frame, text=text)
        l.grid(row=self._row, column=0, columnspan=2, sticky="w", pady=(8, 2))
        self._row += 1
        if lid is None:
            lid = text
        self._labels[lid] = l

    def file(
        self, label: str, vid: str | None = None, filters: str | None = None
    ) -> None:
        types = _parse_filters(filters)

        def build(parent) -> Callable[[], str | None]:
            var = parent.var = tk.StringVar(master=parent)
            ttk.Entry(parent, textvariable=var, width=40).pack(
                side="left", fill="x", expand=True
            )

            def browse() -> None:
                path = filedialog.askopenfilename(filetypes=types)
                if path:
                    var.set(path)

            ttk.Button(parent, text="Browse...", command=browse).pack(
                side="left", padx=(4, 0)
            )
            return var.get

        self._add_row(label, vid, build)

    def savefile(
        self, label: str, vid: str | None = None, filters: str | None = None
    ) -> None:
        types = _parse_filters(filters)

        def build(parent) -> Callable[[], str | None]:
            var = parent.var = tk.StringVar(master=parent)
            ttk.Entry(parent, textvariable=var, width=40).pack(
                side="left", fill="x", expand=True
            )

            def browse() -> None:
                path = filedialog.asksaveasfilename(filetypes=types)
                if path:
                    var.set(path)

            ttk.Button(parent, text="Browse...", command=browse).pack(
                side="left", padx=(4, 0)
            )
            return var.get

        self._add_row(label, vid, build)

    def directory(self, label: str, vid: str | None = None) -> None:
        def build(parent) -> Callable[[], str | None]:
            var = parent.var = tk.StringVar(master=parent)
            ttk.Entry(parent, textvariable=var, width=40).pack(
                side="left", fill="x", expand=True
            )

            def browse() -> None:
                path = filedialog.askdirectory()
                if path:
                    var.set(path)

            ttk.Button(parent, text="Browse...", command=browse).pack(
                side="left", padx=(4, 0)
            )
            return var.get

        self._add_row(label, vid, build)

    def boolean(
        self, label: str, vid: str | None = None, default: bool = False
    ) -> None:
        def build(parent) -> Callable[[], bool]:
            var = parent.var = tk.BooleanVar(master=parent, value=default)
            ttk.Checkbutton(
                parent,
                variable=var,
                style="Bare.TCheckbutton",
            ).pack(anchor="w")
            return var.get

        self._add_row(label, vid, build)

    def combo(self, label: str, choices: Choices, vid: str | None = None) -> None:
        def build(parent) -> Callable[[], Any]:
            cb = ttk.Combobox(parent, values=list(choices), state="readonly")
            cb.current(0)
            cb.pack(anchor="w")
            return lambda: choices[cb.get()]

        self._add_row(label, vid, build)

    def radio(self, label: str, choices: Choices, vid: str | None = None) -> None:
        def build(parent) -> Callable[[], str]:
            var = parent.var = tk.StringVar(
                master=parent, value=next(iter(choices.values()))
            )
            for text, value in choices.items():
                ttk.Radiobutton(parent, text=text, value=value, variable=var).pack(
                    anchor="w"
                )
            return var.get

        self._add_row(label, vid, build, top_align=True)

    def checkboxes(
        self,
        label: str,
        choices: Choices,
        default: bool = False,
        vid: str | None = None,
        columns: int = 4,
    ) -> None:
        if columns < 1:
            raise ValueError("columns must be at least 1")

        def build(parent) -> Callable[[], list]:
            vars_: list[tuple[str, tk.BooleanVar]] = []
            parent.vars = vars_

            for index, (text, value) in enumerate(choices.items()):
                var = tk.BooleanVar(master=parent, value=default)
                ttk.Checkbutton(
                    parent,
                    text=text,
                    variable=var,
                ).grid(
                    row=index // columns,
                    column=index % columns,
                    sticky="w",
                    padx=2,
                    pady=2,
                )
                vars_.append((value, var))

            button_row = (len(choices) + columns - 1) // columns
            button_frame = ttk.Frame(parent)
            button_frame.grid(
                row=button_row,
                column=0,
                columnspan=columns,
                sticky="w",
                pady=(4, 0),
            )

            def set_all(value: bool) -> None:
                for _, v in vars_:
                    v.set(value)

            ttk.Button(
                button_frame, text="[x]", width=3, command=lambda: set_all(True)
            ).pack(side="left", padx=(0, 4))
            ttk.Button(
                button_frame, text="[ ]", width=3, command=lambda: set_all(False)
            ).pack(side="left")

            return lambda: [value for value, var in vars_ if var.get()]

        self._add_row(label, vid, build, top_align=True)

    def textinput(self, label: str, vid: str | None = None, hint: str = "") -> None:
        def build(parent) -> Callable[[], str]:
            entry = _HintEntry(parent, hint=hint, width=40)
            entry.pack(anchor="w", fill="x", expand=True)
            return entry.get

        self._add_row(label, vid, build)

    def integer(
        self,
        label: str,
        vid: str | None = None,
        low: int | None = 0,
        high: int | None = None,
        default: int | None = None,
    ) -> None:
        lo = low if low is not None else -(2**31)
        hi = high if high is not None else 2**31 - 1

        def build(parent) -> Callable[[], str]:
            row = ttk.Frame(parent)
            spin = ttk.Spinbox(row, from_=lo, to=hi, width=10)
            d = default if default is not None else (low if low is not None else 0)
            spin.set(d)
            spin.grid(row=0, column=0)
            ttk.Button(row, text="R", width=2, command=lambda: spin.set(d)).grid(row=0, column=1)
            row.pack(anchor="w")
            return spin.get

        self._add_row(label, vid, build)

    def button(self, text: str, handler: Callable[[], None]) -> None:
        if self._button_row is None:
            self._button_row = ttk.Frame(self._frame)
            self._button_row.grid(
                row=self._row, column=0, columnspan=2, sticky="w", pady=(12, 0)
            )
            self._row += 1
        ttk.Button(self._button_row, text=text, command=handler).pack(
            side="left", padx=(0, 6)
        )

    def break_row(self) -> None:
        self._button_row = None

    def set_label(self, lid: str, text: str) -> None:
        self._labels[lid].configure(text=text)

    def __getitem__(self, vid: str) -> Any:
        return self._getters[vid]()

    def run(self) -> None:
        self.root.transient(self.master)
        self.root.lift()
        self.root.grab_set()
        self.root.focus_force()
        self.center()
        self.root.update_idletasks()
        self.root.deiconify()
