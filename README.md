# Endoscope

A tool for datamining Endacopia (and maybe other games that use AGS 3.6.0 and
have a single data file).

Features:

- Use as a Python library or a command line tool.
- Unpack assets (`unpack`). Supports `.exe`, `.ags`, and `.vox`.
- Unpack sprites (`sprites`). Uses threads to speed up extraction.
- Export game data (from `game28.dta`) to JSON (`data`).
- Export view/animation frames (`view export`).
- Export view data to JSON (`view json`).
- Print info about a view (`view info`).
- Look up which views reference a given sprite ID (`view lookup`).
- Rename extracted audio files to the names used in the scripts
  (`audio rename`). You can extract the assets with either `unpack` or
  AGSUnpacker.

Licensed under the MIT license.

## Planned features / TODO

- **Tkinter GUI.** Some people prefer GUI to CLI, so a portable and
  Python-native GUI would be appreciated.
- **Room background extraction.** Room backgrounds are similar to sprites, but
  rooms in AGS use a different, block-based binary format.

## Installation

### Windows EXE

For Windows, a Pyinstaller .exe is available. Download the
[latest release](https://github.com/bequidox74/endoscope/releases) and extract
the archive. You can optionally add the extracted directory to your PATH to
easily use the program from the command line.

### Python module

You can use `pip` to install the project as an editable package. Run
`pip install -e .` from the project root directory. To later uninstall, run
`pip uninstall -e .`.

## Usage

When installed and added to your PATH, you can run it directly from the command
line. All commands have help messages.

## Python dependencies

Python dependencies are listed in `pyproject.toml`.

- [tabulate](https://pypi.org/project/tabulate/) for formatting tabular data.
- [numpy](https://pypi.org/project/numpy/) because sprite extraction is horribly
  slow otherwise.
