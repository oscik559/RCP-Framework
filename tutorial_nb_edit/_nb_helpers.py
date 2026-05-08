"""
Shared helpers for the per-layer notebook builders.

Each `_build_<layer>.py` script imports `md`, `py`, and `write_nb` from this
module and supplies its own `CELLS` list. We keep this lightweight (no
nbformat dependency) so the build is reproducible from a stock Python.

    md("...")  -> markdown cell
    py("...")  -> code cell
    write_nb(path, cells)

Cell payloads accept either a string or an iterable of strings (joined with "\\n").
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Iterable

KERNELSPEC = {
    "display_name": "Python 3 (.venv)",
    "language": "python",
    "name": "python3",
}
LANG_INFO = {
    "name": "python",
    "version": "3.12",
    "mimetype": "text/x-python",
    "file_extension": ".py",
    "pygments_lexer": "ipython3",
    "codemirror_mode": {"name": "ipython", "version": 3},
}


def _src(payload: str | Iterable[str]) -> list[str]:
    """Normalize cell source to nbformat's list-of-lines convention."""
    if isinstance(payload, str):
        text = textwrap.dedent(payload).strip("\n")
    else:
        text = textwrap.dedent("\n".join(payload)).strip("\n")
    lines = text.split("\n")
    return [ln + ("\n" if i < len(lines) - 1 else "") for i, ln in enumerate(lines)]


def md(payload: str | Iterable[str]) -> dict:
    return {"cell_type": "markdown", "metadata": {}, "source": _src(payload)}


def py(payload: str | Iterable[str]) -> dict:
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": _src(payload),
    }


def write_nb(path: Path, cells: list[dict]) -> None:
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": KERNELSPEC,
            "language_info": LANG_INFO,
        },
        "nbformat": 4,
        "nbformat_minor": 5,
    }
    path.write_text(json.dumps(nb, indent=1, ensure_ascii=False), encoding="utf-8")
    here = path.resolve().parent
    print(f"wrote {path.relative_to(here.parent)}  ({len(cells)} cells)")
