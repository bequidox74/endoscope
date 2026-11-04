import textwrap
import tkinter.messagebox as mbox
from pathlib import Path

from endoscope._internal.utils import is_program_files


def error(msg: str) -> None:
    mbox.showerror("Error", msg)


def check_program_files(p: Path) -> bool:
    if is_program_files(p):
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
            return False
    return True
