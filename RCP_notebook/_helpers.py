"""
Tutorial helpers — kept tiny on purpose.

Anything genuinely reusable across the three notebooks lives here so cells stay
focused on narrative. If you find yourself reaching for these often, the
notebooks themselves are the right place to inline the real logic.
"""

from __future__ import annotations

import json
import os
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterable


def pin_project_root() -> Path:
    """
    Walk up from CWD until we find pyproject.toml, then chdir there.

    Notebooks are run from RCP_notebook/ but the project's relative paths
    (database/harvested.db, Layer_*/...) are written assuming CWD == project
    root. This makes both work.
    """
    here = Path.cwd().resolve()
    for candidate in [here, *here.parents]:
        if (candidate / "pyproject.toml").exists():
            os.chdir(candidate)
            return candidate
    raise RuntimeError(f"could not locate project root from {here}")


def configure_utf8_stdout() -> None:
    """Match the pattern in main.py so Swedish + emoji print cleanly on Windows."""
    if sys.platform.startswith("win"):
        os.environ["PYTHONIOENCODING"] = "utf-8"
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass


def env_probe(check_ollama: bool = False) -> dict:
    """
    Return a dict of {component: status} so a single notebook cell can show
    what's reachable. Doesn't raise — caller decides how strict to be.
    """
    status: dict[str, str] = {}
    status["python"] = sys.version.split()[0]

    for pkg in ("langgraph", "chromadb", "flask", "fitz", "PIL", "requests"):
        try:
            mod = __import__(pkg)
            status[pkg] = getattr(mod, "__version__", "ok")
        except ImportError as e:
            status[pkg] = f"MISSING ({e})"

    root = Path.cwd()
    for db in ("database/harvested.db", "database/agentic.db"):
        p = root / db
        status[db] = f"{p.stat().st_size // 1024} KB" if p.exists() else "MISSING"

    if check_ollama:
        try:
            import requests as _r

            r = _r.get("http://localhost:11434/api/tags", timeout=2)
            tags = [m["name"] for m in r.json().get("models", [])]
            status["ollama"] = f"reachable, {len(tags)} models"
        except Exception as e:
            status["ollama"] = f"unreachable ({type(e).__name__})"

    return status


def print_table(rows: Iterable[Iterable[Any]], headers: list[str], max_col: int = 60) -> None:
    """
    Plain-text table printer — replaces pandas for the tutorial.

    Truncates long cells so wide JSON blobs don't blow up the layout.
    """
    rows = [
        [(_truncate(str(v), max_col)) for v in row] for row in rows
    ]
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    def line(parts: list[str]) -> str:
        return " | ".join(p.ljust(widths[i]) for i, p in enumerate(parts))

    print(line(headers))
    print("-+-".join("-" * w for w in widths))
    for row in rows:
        print(line(row))


def _truncate(s: str, n: int) -> str:
    s = s.replace("\n", " ")
    return s if len(s) <= n else s[: n - 1] + "…"


def query(db_path: str, sql: str, params: tuple = ()) -> tuple[list[str], list[tuple]]:
    """sqlite3 wrapper that returns (column_names, rows) — no pandas dep."""
    with sqlite3.connect(db_path) as con:
        cur = con.execute(sql, params)
        cols = [d[0] for d in cur.description] if cur.description else []
        rows = cur.fetchall()
    return cols, rows


def show_query(db_path: str, sql: str, params: tuple = (), max_col: int = 60) -> None:
    """Run sql and pretty-print the result."""
    cols, rows = query(db_path, sql, params)
    if not rows:
        print(f"(no rows)\n  sql: {sql}")
        return
    print_table(rows, cols, max_col=max_col)
    print(f"\n{len(rows)} row(s)")


def pdf_page_image(pdf_path: str | Path, page_index: int, dpi: int = 130):
    """Render one PDF page as a PIL.Image — Jupyter displays it inline."""
    import fitz  # PyMuPDF
    from PIL import Image

    with fitz.open(str(pdf_path)) as doc:
        page = doc.load_page(page_index)
        pix = page.get_pixmap(dpi=dpi)
        return Image.frombytes("RGB", (pix.width, pix.height), pix.samples)


def pretty_state(state: dict, max_str: int = 80) -> None:
    """Single-screen view of a SessionState dict — long values truncated."""
    width = max(len(k) for k in state) + 2
    for k, v in state.items():
        if isinstance(v, (dict, list)):
            v = json.dumps(v, default=str)
        s = _truncate(repr(v), max_str)
        print(f"{k.ljust(width)} {s}")


@contextmanager
def silenced_stdout():
    """Temporarily mute prints — useful around chatty library setup."""
    import io

    old = sys.stdout
    sys.stdout = io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old
