# Endoscope

A tool for datamining Endacopia (and maybe other games that use AGS 3.6.0 and
have a single data file).

Features:

- Use as a Python library or a command line tool.
- Unpack assets (`unpack`). Supports `.exe`, `.ags`, and `.vox`.
- Export game data (from `game28.dta`) to JSON (`data`).
- Export view/animation frames (`view export`).
  - ⚠️ You will have to extract the sprites first with
    [AGSUnpacker](https://github.com/adm244/AGSUnpacker). Endoscope can not
    (yet) decode the sprites itself.
- Export view data to JSON (`view json`).
- Print info about a view (`view info`).
- Look up which views reference a given sprite ID (`view lookup`).
- Rename extracted audio files to the names used in the scripts
  (`audio rename`). You can extract the assets with either `unpack` or
  AGSUnpacker.

Licensed under the MIT license.

## Planned features / TODO

- **Self-sufficiency for sprite extraction.** Extraction of sprites from AGS
  games is rather complicated. Sprites with at most 256 colors get stored as
  indices into a pallete, otherwise they are stored directly. Sprite data may be
  compressed with RLE or LZW (depending on the game), and naive porting of the
  corresponding C++ routines to Python results in horrible performance. numpy is
  usually required, which makes things all the more complicated.
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
