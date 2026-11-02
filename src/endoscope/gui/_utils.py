import tkinter.messagebox as mbox


def error(msg: str) -> None:
    mbox.showerror("Error", msg)


def warn(msg: str) -> None:
    mbox.showwarning("Warning", msg)
