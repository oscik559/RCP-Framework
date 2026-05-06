"""
Generator for the three tutorial notebooks.

We build .ipynb files as plain JSON dicts so this script doesn't add a
nbformat / jupyter dependency. Re-run this script any time you tweak content
below — it overwrites the .ipynb files in place.

    python tutorial_nb_edit/_build.py

The notebooks themselves carry the narrative; this file is purely scaffolding.
Cells are added via:
    md("...")  -> markdown cell
    py("...")  -> code cell

Cell payloads accept either a string or a list of strings (joined with "\n").
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Iterable

HERE = Path(__file__).resolve().parent
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
    print(f"wrote {path.relative_to(HERE.parent)}  ({len(cells)} cells)")


# =====================================================================
# Notebook 1 — Layer 1: Extraction
# =====================================================================

L1_CELLS: list[dict] = [
    md("""
        # Layer 1 — Extraction
        ### From PDF catalog to a queryable SQLite database

        This notebook walks the **extraction pipeline** that turns the Hydroscand
        product catalog (Swedish-language PDFs) into the structured database
        `database/harvested.db` that the rest of the framework queries.

        **What you'll see**

        | Stage | Output                            | Cell focus                        |
        |-------|-----------------------------------|-----------------------------------|
        | 0     | `product_knowledge` rows          | Intro pages → assembly text       |
        | 1     | `Layer_1b/data/png_pages/*.png`   | PDF pages rendered as images      |
        | 2     | `page_regions` rows               | Header/footer detection           |
        | 2b/3a | `categories`, `product_families`  | VLM-extracted hierarchy           |
        | 3b    | `products` rows                   | Per-SKU specs (full-text indexed) |

        **Default mode is read-only.** The shipped `harvested.db` is already
        populated, so cells below *inspect* what each stage produced. To re-run
        the full pipeline against a fresh PDF, flip the `RERUN_EXTRACTION` flag
        in the optional section near the bottom.

        **Prerequisites** — see [SETUP.md](../SETUP.md). You only need full
        re-extraction (Ollama + `qwen2-vl`) if you flip the flag.
    """),
    md("""
        ## 0. Open the project from the right place

        Notebooks live in `tutorial_nb_edit/` but the project's relative paths
        (e.g. `database/harvested.db`) assume CWD == project root. The first
        cell pins us there and configures UTF-8 stdout — Swedish characters in
        the catalog will mangle on Windows otherwise.
    """),
    py("""
        # Pin CWD to project root and make stdout safe for Swedish text.
        import sys
        sys.path.insert(0, str(__import__("pathlib").Path.cwd()))  # so _helpers.py imports
        from _helpers import pin_project_root, configure_utf8_stdout, env_probe

        ROOT = pin_project_root()
        configure_utf8_stdout()
        print("project root:", ROOT)
    """),
    py("""
        # Probe the environment. Anything marked MISSING means a later cell
        # may fail — fix it before continuing.
        for k, v in env_probe(check_ollama=False).items():
            print(f"{k:30s} {v}")
    """),
    md("""
        ## 1. The source PDFs

        Three Swedish-language Hydroscand PDFs live alongside the extraction
        scripts. They are publicly available (Hydroscand publishes them on
        their site), so you can swap in your own copy if these change.
    """),
    py("""
        from pathlib import Path

        PDF_DIR = Path("Layer_1_Extraction/Case_I/Layer_1b")
        for pdf in sorted(PDF_DIR.glob("*.pdf")):
            kb = pdf.stat().st_size // 1024
            print(f"{pdf.name:30s} {kb:>6} KB")
    """),
    md("""
        ### Render a page inline

        PyMuPDF (`fitz`) is already in the project's deps. We use it as a
        lightweight visual sanity check before any extraction logic runs.
    """),
    py("""
        # Try it: change PAGE_INDEX or PDF_NAME below and re-run.
        from _helpers import pdf_page_image

        PDF_NAME   = "Produktbok_2020.pdf"
        PAGE_INDEX = 8        # 0-based — flip this to look at other pages

        pdf_page_image(PDF_DIR / PDF_NAME, PAGE_INDEX, dpi=120)
    """),
    md("""
        ## 2. Stage 0 — knowledge extraction

        `0_extract_knowledge.py` reads catalog intro pages (assembly
        instructions, standards, ToCs) into `product_knowledge`. These rows
        carry **prose** — the kind of text the reasoning agent later cites
        when an answer needs context beyond a row of numbers.

        > Heads-up: in the shipped `harvested.db`, `product_knowledge` is
        > **empty** — the prose layer was set aside in the published
        > artefact. The cells below will report 0 rows. Re-run Stage 0
        > (see §8 below) to populate it.
    """),
    py("""
        from _helpers import show_query

        DB = "database/harvested.db"
        show_query(DB, '''
            SELECT knowledge_type, COUNT(*) AS n, content_language
            FROM product_knowledge
            GROUP BY knowledge_type, content_language
            ORDER BY n DESC
        ''')
    """),
    py("""
        # Once Stage 0 has been re-run, this prints one full prose record.
        # Try it: change knowledge_type to ASSEMBLY / STANDARDS / TOC.
        from _helpers import query

        cols, rows = query(DB, '''
            SELECT pdf_name, page_number, section_title, content
            FROM product_knowledge
            WHERE knowledge_type = ?
            LIMIT 1
        ''', ("DESCRIPTION",))
        if rows:
            r = dict(zip(cols, rows[0]))
            print(f"[{r['pdf_name']} p.{r['page_number']}]  {r['section_title']}\\n")
            print(r["content"][:1200], "..." if len(r["content"]) > 1200 else "")
        else:
            print("(no rows — re-run Stage 0; see §8)")
    """),
    md("""
        ## 3. Stage 1 — PDF → PNG

        `1_pdf_to_png.py` rasterises every page so downstream stages can run
        a Vision Language Model on them. Rendered PNGs are gitignored — if
        the folder is empty, that's expected; the cell handles it gracefully.
    """),
    py("""
        from pathlib import Path
        png_dir = Path("Layer_1_Extraction/Case_I/Layer_1b/data/png_pages")
        if not png_dir.exists():
            print(f"{png_dir} not present — re-run Stage 1 to populate.")
        else:
            pngs = sorted(png_dir.glob("*.png"))
            print(f"{len(pngs)} rendered pages.")
            for p in pngs[:5]:
                print(" -", p.name)
    """),
    md("""
        ## 4. Stage 2 — page regions

        `2_detect_headers_footers.py` records header/footer bounding boxes
        per page so later VLM prompts can ignore boilerplate. One row per
        page, per source PDF.
    """),
    py("""
        # Counts per PDF.
        show_query(DB, '''
            SELECT pdf_name, COUNT(*) AS pages
            FROM page_regions
            GROUP BY pdf_name
            ORDER BY pages DESC
        ''')
    """),
    py("""
        # Sample row — bounding boxes are normalized page coords.
        show_query(DB, '''
            SELECT pdf_name, page_number,
                   header_x0, header_y0, header_x1, header_y1,
                   footer_x0, footer_y0, footer_x1, footer_y1
            FROM page_regions
            ORDER BY pdf_name, page_number
            LIMIT 5
        ''', max_col=14)
    """),
    md("""
        ## 5. Stages 2b / 3a — categories and families

        Stage 2b extracts top-level categories (e.g. SPIRALSLANG). Stage 3a
        groups products into families that share specs (e.g. hose family
        4201). Together they're the "shape" of the catalog.
    """),
    py("""
        show_query(DB, "SELECT id, name, chapter, page_number FROM categories ORDER BY name LIMIT 20", max_col=80)
    """),
    py("""
        # Try it: change CAT to one of the names printed above
        # (the shipped DB has HÖGTRYCKSSLANG and PRESSKOPPLINGAR).
        CAT = "HÖGTRYCKSSLANG"
        show_query(DB, '''
            SELECT pf.family_code, pf.name AS family_name, pf.description
            FROM product_families pf
            JOIN categories c ON c.id = pf.category_id
            WHERE c.name = ?
            ORDER BY pf.family_code
            LIMIT 15
        ''', (CAT,))
    """),
    md("""
        ## 6. Stage 3b — products (the actual SKUs)

        Each row in `products` is one SKU with a JSON spec blob. The blob is
        what the reasoning engine ultimately quotes from when it answers a
        natural-language query.
    """),
    py("""
        # Counts by family, top 10.
        show_query(DB, '''
            SELECT pf.family_code, COUNT(p.id) AS n
            FROM products p
            JOIN product_families pf ON pf.id = p.family_id
            GROUP BY pf.family_code
            ORDER BY n DESC
            LIMIT 10
        ''')
    """),
    py("""
        # One full record so you see the JSON spec.
        # Try it: change PRODUCT_CODE to anything that appeared above.
        import json as _json
        from _helpers import query

        PRODUCT_CODE = "1071-00-16"
        cols, rows = query(DB, "SELECT * FROM products WHERE product_code = ?", (PRODUCT_CODE,))
        if rows:
            row = dict(zip(cols, rows[0]))
            for k, v in row.items():
                if k.endswith("_json") or (isinstance(v, str) and v.startswith("{")):
                    try:
                        v = _json.dumps(_json.loads(v), indent=2, ensure_ascii=False)
                    except Exception:
                        pass
                print(f"--- {k} ---\\n{v}\\n")
        else:
            print(f"no row for {PRODUCT_CODE} — pick a product_code from the table above.")
    """),
    md("""
        ## 7. Lexical search over family applications

        The extraction pipeline also builds FTS5 indexes (`product_families_fts`,
        `product_knowledge_fts`) — these are what Layer 2 strategies hit when
        a query needs keyword search before semantic re-ranking. We don't
        exercise FTS5 directly here (the shipped index is contentless; doing
        so cleanly takes a couple of cells). For a quick demo, a `LIKE` over
        the same content works fine.
    """),
    py("""
        # Try it: change Q to a Swedish or English term that might appear
        # in family descriptions (e.g. "tryck", "boiling", "marin").
        Q = "tryck"
        show_query(DB, '''
            SELECT family_code, name, applications
            FROM product_families
            WHERE applications LIKE ?
            ORDER BY family_code
            LIMIT 5
        ''', (f"%{Q}%",), max_col=80)
    """),
    md("""
        ## 8. Optional — re-run extraction on a fresh PDF

        Everything above was read-only. Flip the flag below to actually run
        the extraction scripts. You need:

        - **Ollama** running locally (`ollama serve`)
        - The vision model: `ollama pull qwen2-vl`
        - Plenty of patience — Stage 3b alone runs the VLM on every page

        > ⚠️ Re-running overwrites the **shipped** `database/harvested.db`.
        > If you want to keep the original, copy it aside first:
        > `cp database/harvested.db database/harvested.db.backup`
    """),
    py("""
        RERUN_EXTRACTION = False     # flip to True to actually execute

        if RERUN_EXTRACTION:
            import subprocess, sys
            scripts = [
                "Layer_1_Extraction/Case_I/Layer_1b/0_extract_knowledge.py",
                "Layer_1_Extraction/Case_I/Layer_1b/1_pdf_to_png.py",
                "Layer_1_Extraction/Case_I/Layer_1b/2_detect_headers_footers.py",
                "Layer_1_Extraction/Case_I/Layer_1b/2b_extract_categories.py",
                "Layer_1_Extraction/Case_I/Layer_1b/3a_extract_families.py",
                "Layer_1_Extraction/Case_I/Layer_1b/3b_extract_products_vlm.py",
            ]
            for s in scripts:
                print(f"\\n=== {s} ===")
                subprocess.run([sys.executable, s], check=True)
        else:
            print("RERUN_EXTRACTION is False — skipping. The shipped DB is intact.")
    """),
    md("""
        ## 9. Validate the database

        `db_utils.py --verify` prints row counts per table. Treat it as the
        canonical "is the DB sane?" check.
    """),
    py("""
        import subprocess, sys
        subprocess.run([sys.executable, "database/db_utils.py", "--verify"], check=False)
    """),
    md("""
        ## You've finished Layer 1

        - The PDF → DB pipeline is six stages, each writing into a specific table.
        - The shipped database is enough to drive every Layer 2 / Layer 3 demo.
        - Re-extraction is opt-in; the default is read-only inspection.

        **Next:** [02_agentic_reasoning.ipynb](./02_agentic_reasoning.ipynb) — how the
        reasoning engine queries this database to answer natural-language
        questions.
    """),
]


# =====================================================================
# Notebook 2 — Layer 2: Agentic Reasoning
# =====================================================================

L2_CELLS: list[dict] = [
    md("""
        # Layer 2 — Agentic Reasoning  *(standalone notebook)*
        ### A faithful reimplementation of `Layer_2_Agentic_Reasoning/` in cells

        This notebook is **standalone**. It contains the entire reasoning
        framework — schema creation, template seeding, the LangGraph state
        machine, the workflow nodes, the function library, and the prompts —
        as cells you can read, run, and modify.

        Send a friend this `.ipynb` plus `harvested.db`. They run top-to-bottom
        and have a working agentic Q&A system over the Hydroscand product catalog.

        **What gets created**

        | Built in | What it is |
        |----------|------------|
        | §3 | `agentic.db` from a 9-table SQL schema, in your working directory |
        | §4 | Seven strategies + fourteen function templates seeded into `agentic.db` |
        | §6 | Six executable functions — the *function library* the workflow can call |
        | §7 | Seven LangGraph nodes (`GoalDefine`, `StrategyPlan`, `FunctionExecute`, …) |
        | §8 | A compiled state machine with **tri-condition routing** (continue / abort / succeed) |
        | §9 | End-to-end runs against real queries |

        **What this notebook deliberately simplifies** (so it stays readable):

        | Simplification | What it means |
        |----------------|---------------|
        | **No `DatabaseManager` wrapper** | The production project has a 1200-line `DatabaseManager` class that mediates every SQL call. We use direct `sqlite3.connect(...).execute(...)` instead — readable but less safe under concurrency. |
        | **No parallel execution** | The `[Func1 \\|\\| Func2]` syntax in `PlanSteps` and the `concurrent.futures` dispatch path are skipped. Everything runs sequentially. |
        | **No async helpers** | The production `async_helpers.py` (~450 lines) is dropped — we keep blocking calls only. |
        | **No vector / embedding search** | Semantic retrieval (ChromaDB + `nomic-embed-text`) is skipped. The notebook's `Search Products` falls back to SQL `LIKE`. |
        | **6 of 15 functions** | We implement representative functions: Extract Product Number, Extract Requirements, Query Database, Search Products, Search Families, Extract Attributes, Analyze With LLM. The full library has 15. |
        | **No multi-tier LLM** | The production system splits "basic" / "reasoning" / "multimodal" models. We use one model (`llama3.2:latest`) for every LLM call. |
        | **No retry / debug dispatcher** | `invoke_llm_with_retry`, `debug_config.set_debug_level(N)`, and the prompt-loader YAML system are inlined as plain calls + a `VERBOSE` flag. |

        The full project at [Layer_2_Agentic_Reasoning/](../Layer_2_Agentic_Reasoning/) has all of these. Where a cell below skips a feature, a callout flags it inline.

        **Prerequisites**

        - `harvested.db` next to this notebook (or path adjusted in §1).
        - Python 3.10+ with `langgraph`, `requests` installed:
          ```
          pip install langgraph requests
          ```
        - Ollama running locally with a model pulled:
          ```
          ollama pull llama3.2:latest
          ```
    """),

    md("""
        ### Notebook map

        | § | Title | What you do |
        |---|-------|-------------|
        | §1 | Setup | Paths, imports, environment probe |
        | §2 | Tour `harvested.db` | Sanity-check the product data |
        | §3 | Build `agentic.db` | Create the 9-table workflow schema |
        | §4 | Seed templates | Strategies, function templates, params, outputs |
        | §5 | Session state | The dict that flows through the graph |
        | §6 | Function library | Six executable functions + LLM helper + prompts |
        | §7 | Workflow nodes | Seven node functions + small DB helpers |
        | §8 | Build LangGraph | Compile the state machine, render its shape |
        | §9 | Run queries | End-to-end runs, traced per node |

        > **Tip:** §3, §4, §6, §7 just *define* things — running them is fast.
        > §9 *invokes the LLM* — those are the slow ones (a few seconds per
        > stage on a local model).
    """),
    md("""
        ## §1. Setup — paths, imports, environment probe

        Edit `DB_HARVESTED` if your `.db` lives elsewhere. `DB_AGENTIC` will
        be **created** from scratch in §3, so the path just needs to be
        writable.
    """),
    py("""
        # ---- standard library ----
        import json
        import os
        import re
        import sqlite3
        import sys
        import time
        from pathlib import Path
        from typing import Any, Callable, Dict, List, Optional, Tuple
        from typing_extensions import TypedDict

        # ---- third-party ----
        import requests                                   # talks to Ollama
        from langgraph.graph import END, StateGraph       # the state machine

        # ---- where the databases live ----
        DB_HARVESTED = "harvested.db"             # the product data your friend ships with
        DB_AGENTIC   = "agentic.db"               # workflow state — we create this in §3

        # ---- LLM endpoint ----
        OLLAMA_URL   = "http://localhost:11434"
        OLLAMA_MODEL = "llama3.2:latest"

        # ---- UTF-8 for Swedish text on Windows ----
        if sys.platform.startswith("win"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        print("python    :", sys.version.split()[0])
        print(f"{DB_HARVESTED:25s}",
              f"{Path(DB_HARVESTED).stat().st_size // 1024} KB" if Path(DB_HARVESTED).exists() else "MISSING")
        print(f"{DB_AGENTIC:25s}",
              "(will be created in §3)" if not Path(DB_AGENTIC).exists() else
              f"{Path(DB_AGENTIC).stat().st_size // 1024} KB (existing — will be reset in §3)")
        try:
            r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=2)
            tags = [m["name"] for m in r.json().get("models", [])]
            print(f"ollama                    reachable, {len(tags)} models")
            if OLLAMA_MODEL not in tags:
                print(f"  ⚠️  '{OLLAMA_MODEL}' not pulled. Run: ollama pull {OLLAMA_MODEL}")
        except Exception as e:
            print(f"ollama                    UNREACHABLE — fix this before §6+. ({e})")
    """),

    md("""
        ## §2. Quick tour of `harvested.db`

        Sanity check we can read the product data the workflow will query.
        This DB has three layers of hierarchy: `categories` → `product_families`
        → `products`. The `products.specifications` column holds a JSON spec
        sheet per SKU.
    """),
    py("""
        def db_query(db_path: str, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
            \"\"\"Run SELECT, return list of dicts. We'll reuse this everywhere.\"\"\"
            with sqlite3.connect(db_path) as con:
                cur = con.execute(sql, params)
                cols = [d[0] for d in cur.description] if cur.description else []
                return [dict(zip(cols, row)) for row in cur.fetchall()]


        for tbl in ("categories", "product_families", "products"):
            n = db_query(DB_HARVESTED, f"SELECT COUNT(*) AS n FROM {tbl}")[0]["n"]
            print(f"  {tbl:20s} {n:>5} rows")

        sample = db_query(DB_HARVESTED,
                          "SELECT product_code, family_id FROM products WHERE product_code = ?",
                          ("1071-00-16",))
        print("\\nsample lookup 1071-00-16 →", sample)
    """),

    md("""
        # §3. Build `agentic.db` from scratch

        The framework keeps two databases:
        - `harvested.db` — **product** data (read-only here).
        - `agentic.db` — **workflow** state. Stores every goal, strategy, function call, parameter, and output, plus the **template libraries** the planner reads from.

        The schema has a Goal → Strategy → Function hierarchy mirrored across
        two halves: `*InSession` tables (per-run execution traces) and `*Library`
        tables (reusable templates).

        ```mermaid
        erDiagram
            GoalInSession                ||--o{ StrategyInSession           : "has many"
            StrategyInSession            ||--o{ FunctionInSession           : "has many"
            FunctionInSession            ||--o{ FunctionOutputInSession     : "produces"
            FunctionInSession            ||--o{ FunctionParametersInSession : "consumes"

            StrategyLibrary              }o..o| StrategyInSession           : "template for"
            FunctionTemplateLibrary      }o..o| FunctionInSession           : "template for"
            FunctionTemplateLibrary      ||--o{ FunctionParametersLibrary   : "declares"
            FunctionTemplateLibrary      ||--o{ FunctionOutputLibrary       : "declares"
        ```

        Two halves, same shape:
        - **`*Library`** rows are the *catalog* — what strategies and functions exist.
        - **`*InSession`** rows are the *log* — what actually ran for each query, with what params, what outputs, and what success status.

        The SQL below is lifted verbatim from `Layer_2_Agentic_Reasoning/db/agentic_schema.sql`.

        > **Simplified:** The production project routes every SQL call through a `DatabaseManager` class (~1200 lines) that handles connection pooling, retries, and a session-scoped API. Here we just call `sqlite3.connect(...).execute(...)` directly. Easier to read; not safe under concurrent writes.
    """),
    py("""
        SCHEMA_SQL = '''
        -- ─── Core Workflow Tables ─────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS GoalInSession(
            GoalID          INTEGER PRIMARY KEY AUTOINCREMENT,
            SessionID       INTEGER,
            GoalName        TEXT,
            GoalTarget      TEXT,
            GoalValidation  TEXT,
            GoalDescription TEXT,
            GoalSuccess     INTEGER  -- NULL=pending, 0=failed, 1=success
        );

        CREATE TABLE IF NOT EXISTS StrategyInSession(
            StrategyID          INTEGER PRIMARY KEY AUTOINCREMENT,
            GoalID              INTEGER,
            StrategyName        TEXT,
            StrategyTarget      TEXT,
            StrategyDescription TEXT,
            PlanSteps           TEXT,
            StrategySuccess     INTEGER,
            StrategyValidation  TEXT,
            FOREIGN KEY(GoalID) REFERENCES GoalInSession(GoalID)
        );

        CREATE TABLE IF NOT EXISTS FunctionInSession(
            FunctionID      INTEGER PRIMARY KEY AUTOINCREMENT,
            StrategyID      INTEGER,
            StrategyName    TEXT,
            FunctionName    TEXT,
            FunctionSuccess INTEGER,
            failedtext      TEXT,
            FOREIGN KEY(StrategyID) REFERENCES StrategyInSession(StrategyID)
        );

        CREATE TABLE IF NOT EXISTS FunctionOutputInSession(
            FunctionOutputID INTEGER PRIMARY KEY AUTOINCREMENT,
            FunctionID       INTEGER,
            FunctionName     TEXT,
            StrategyName     TEXT,
            OutputName       TEXT,
            OutputValue      TEXT,
            Type             TEXT,
            FOREIGN KEY(FunctionID) REFERENCES FunctionInSession(FunctionID)
        );

        CREATE TABLE IF NOT EXISTS FunctionParametersInSession(
            FunctionParameterID INTEGER PRIMARY KEY AUTOINCREMENT,
            FunctionID          INTEGER,
            FunctionName        TEXT,
            StrategyName        TEXT,
            ParameterName       TEXT,
            ParameterValue      TEXT,
            Type                TEXT,
            FOREIGN KEY(FunctionID) REFERENCES FunctionInSession(FunctionID)
        );

        -- ─── Template Libraries ───────────────────────────────────────────
        CREATE TABLE IF NOT EXISTS StrategyLibrary(
            StrategyID          INTEGER PRIMARY KEY AUTOINCREMENT,
            StrategyName        TEXT,
            StrategyTarget      TEXT,
            StrategyDescription TEXT,
            PlanSteps           TEXT
        );

        CREATE TABLE IF NOT EXISTS FunctionTemplateLibrary(
            FunctionTemplateID  INTEGER PRIMARY KEY AUTOINCREMENT,
            FunctionName        TEXT,
            StrategyType        TEXT,
            FunctionDescription TEXT
        );

        CREATE TABLE IF NOT EXISTS FunctionOutputLibrary(
            FunctionOutputID   INTEGER PRIMARY KEY AUTOINCREMENT,
            FunctionTemplateID INTEGER,
            OutputName         TEXT,
            OutputValue        TEXT,
            Type               TEXT,
            FOREIGN KEY(FunctionTemplateID) REFERENCES FunctionTemplateLibrary(FunctionTemplateID)
        );

        CREATE TABLE IF NOT EXISTS FunctionParametersLibrary(
            FunctionParameterID INTEGER PRIMARY KEY AUTOINCREMENT,
            FunctionTemplateID  INTEGER,
            ParameterName       TEXT,
            ParameterValue      TEXT,
            Type                TEXT,
            FOREIGN KEY(FunctionTemplateID) REFERENCES FunctionTemplateLibrary(FunctionTemplateID)
        );

        -- ─── Indexes for navigation/perf ─────────────────────────────────
        CREATE INDEX IF NOT EXISTS idx_strategy_goal           ON StrategyInSession(GoalID);
        CREATE INDEX IF NOT EXISTS idx_function_strategy       ON FunctionInSession(StrategyID);
        CREATE INDEX IF NOT EXISTS idx_function_output_function ON FunctionOutputInSession(FunctionID);
        CREATE INDEX IF NOT EXISTS idx_function_params_function ON FunctionParametersInSession(FunctionID);
        CREATE INDEX IF NOT EXISTS idx_strategy_success         ON StrategyInSession(StrategySuccess);
        CREATE INDEX IF NOT EXISTS idx_function_success         ON FunctionInSession(FunctionSuccess);
        CREATE INDEX IF NOT EXISTS idx_goal_success             ON GoalInSession(GoalSuccess);
        '''


        def init_agentic_db(drop_and_recreate: bool = True) -> None:
            \"\"\"Drop user tables (if asked) and re-create the full schema.\"\"\"
            with sqlite3.connect(DB_AGENTIC) as con:
                cur = con.cursor()
                if drop_and_recreate:
                    cur.execute("PRAGMA foreign_keys = OFF")
                    for (name,) in cur.execute(
                        "SELECT name FROM sqlite_master "
                        "WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                    ).fetchall():
                        cur.execute(f"DROP TABLE IF EXISTS {name}")
                    cur.execute("PRAGMA foreign_keys = ON")
                cur.executescript(SCHEMA_SQL)
                con.commit()


        init_agentic_db(drop_and_recreate=True)

        # Confirm tables landed.
        tables = db_query(DB_AGENTIC,
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name")
        for t in tables:
            print(" ", t["name"])
    """),
    md("""
        ### 🔍 Inspect — what's inside `agentic.db` right now

        The cell below shows every table's columns and current row count.
        After §3 the libraries and session tables both exist but are empty;
        after §4 the libraries fill up; after §9 the session tables fill up.
        Run this cell at any point to take a snapshot.
    """),
    py("""
        def inspect_db(db_path: str) -> None:
            \"\"\"Tree view of tables, columns, and row counts.\"\"\"
            tabs = db_query(db_path,
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%' ORDER BY name")
            for t in tabs:
                tname = t["name"]
                cnt = db_query(db_path, f"SELECT COUNT(*) AS n FROM {tname}")[0]["n"]
                cols = db_query(db_path, f"PRAGMA table_info({tname})")
                col_str = ", ".join(c["name"] for c in cols)
                bullet = "📂" if cnt else "📄"
                print(f"  {bullet} {tname:32s} {cnt:>4} rows  ({col_str})")


        inspect_db(DB_AGENTIC)
    """),

    md("""
        # §4. Seed the template libraries

        The planner picks strategies and functions by **reading from `agentic.db`**,
        not from hardcoded Python. So before we can run anything, the library
        tables need rows.

        The data below is lifted verbatim from
        `Layer_2_Agentic_Reasoning/logic/templates.py` — seven strategies and
        fourteen function templates. Each strategy's `PlanSteps` is a comma-
        separated list of function names; the planner parses this string.
    """),
    py("""
        # ---- Strategies ---------------------------------------------------
        # (StrategyName, StrategyTarget, StrategyDescription, PlanSteps)
        STRATEGIES_SEED = [
            ("DIRECT SPECIFICATION LOOKUP",
             "lookup",
             "Direct database lookup for specific product specifications. Fast deterministic path.",
             "Extract Product Number, Query Database, Extract Attributes, Analyze With LLM"),

            ("CONTEXTUAL PRODUCT SEARCH",
             "search",
             "Multi-criteria product search with semantic understanding. Application-based queries.",
             "Extract Requirements, Search Products, Extract Attributes, Analyze With LLM"),

            ("STANDARD & COMPLIANCE LOOKUP",
             "compliance",
             "Search products by standards (EN, ISO, SAE) and certifications.",
             "Extract Requirements, Query Database, Extract Attributes, Analyze With LLM"),

            ("KNOWLEDGE BASE & RAG",
             "knowledge",
             "Retrieval for procedural knowledge — assembly instructions, FAQ.",
             "Search Families, Extract Attributes, Analyze With LLM"),

            ("MULTI-PRODUCT COMPARISON",
             "compare",
             "Side-by-side comparison of two or more products identified by code.",
             "Extract Product Number, Query Database, Extract Attributes, Analyze With LLM"),

            ("FAMILY DEEP-DIVE",
             "family",
             "Look up everything about a product family (e.g. KAPPAFLEX, 4201).",
             "Search Families, Extract Attributes, Analyze With LLM"),

            ("TECHNICAL CALCULATION",
             "calculate",
             "Hydraulic engineering calculations (flow rate, pressure drop). Skipped in this notebook.",
             "Extract Requirements, Analyze With LLM"),
        ]

        # ---- Function templates ------------------------------------------
        # (FunctionName, StrategyType, FunctionDescription)
        FUNCTIONS_SEED = [
            ("Extract Product Number", "extract", "LLM extracts product codes from the user query."),
            ("Extract Requirements",   "extract", "LLM extracts structured requirements (pressure/temp/material)."),
            ("Query Database",         "search",  "Lookup by product_code joined to family / category."),
            ("Search Products",        "search",  "Keyword search across products + family applications."),
            ("Search Families",        "search",  "Keyword search across product_families."),
            ("Extract Attributes",     "extract", "Deterministic attribute extraction from prior outputs."),
            ("Analyze With LLM",       "analyze", "Final synthesis — composes the answer from collected evidence."),
        ]

        # ---- Per-function parameters & outputs ---------------------------
        # Param value "Input" means "use the user query directly".
        # Param value "" (empty) means "merge from prior function outputs".
        PARAMS_SEED: Dict[str, List[Tuple[str, str, str]]] = {
            "Extract Product Number": [("Input", "", "string")],
            "Extract Requirements":   [("Input", "", "string")],
            "Query Database": [
                ("query_type", "select", "string"),
                ("table",      "products", "string"),
                ("Keyword Output", "", "string"),  # filled from Extract Product Number
                ("limit",      "100", "integer"),
            ],
            "Search Products":  [("keywords", "Input", "string"), ("limit", "20", "integer")],
            "Search Families":  [("keywords", "Input", "string"), ("limit", "20", "integer")],
            "Extract Attributes": [("items", "", "json"), ("config", "{}", "json")],
            "Analyze With LLM": [
                ("question", "Input", "string"),
                ("Assembled Data", "", "json"),
                ("extracted_data", "", "json"),
            ],
        }

        OUTPUTS_SEED: Dict[str, List[Tuple[str, str, str]]] = {
            "Extract Product Number": [("Keyword Output", "", "string")],
            "Extract Requirements":   [("requirements", "{}", "json")],
            "Query Database":         [("items", "[]", "json"), ("count", "0", "integer")],
            "Search Products":        [("items", "[]", "json"), ("count", "0", "integer")],
            "Search Families":        [("items", "[]", "json"), ("count", "0", "integer")],
            "Extract Attributes":     [("extracted_data", "[]", "json")],
            "Analyze With LLM":       [("Analysis", "", "string")],
        }
    """),

    md("""
        ### Populate the library tables
    """),
    py("""
        def populate_template_libraries() -> None:
            \"\"\"Wipe library tables and reseed with constants from §4.\"\"\"
            with sqlite3.connect(DB_AGENTIC) as con:
                cur = con.cursor()
                cur.executescript('''
                    DELETE FROM StrategyLibrary;
                    DELETE FROM FunctionTemplateLibrary;
                    DELETE FROM FunctionOutputLibrary;
                    DELETE FROM FunctionParametersLibrary;
                ''')

                for sname, starg, sdesc, plan in STRATEGIES_SEED:
                    cur.execute(
                        "INSERT INTO StrategyLibrary "
                        "(StrategyName, StrategyTarget, StrategyDescription, PlanSteps) "
                        "VALUES (?, ?, ?, ?)",
                        (sname, starg, sdesc, plan),
                    )

                for fname, ftype, fdesc in FUNCTIONS_SEED:
                    cur.execute(
                        "INSERT INTO FunctionTemplateLibrary "
                        "(FunctionName, StrategyType, FunctionDescription) VALUES (?, ?, ?)",
                        (fname, ftype, fdesc),
                    )
                    fid = cur.lastrowid
                    for oname, oval, otype in OUTPUTS_SEED.get(fname, []):
                        cur.execute(
                            "INSERT INTO FunctionOutputLibrary "
                            "(FunctionTemplateID, OutputName, OutputValue, Type) VALUES (?, ?, ?, ?)",
                            (fid, oname, oval, otype),
                        )
                    for pname, pval, ptype in PARAMS_SEED.get(fname, []):
                        cur.execute(
                            "INSERT INTO FunctionParametersLibrary "
                            "(FunctionTemplateID, ParameterName, ParameterValue, Type) VALUES (?, ?, ?, ?)",
                            (fid, pname, pval, ptype),
                        )
                con.commit()


        populate_template_libraries()

        # Verify what landed.
        for tbl in ("StrategyLibrary", "FunctionTemplateLibrary",
                    "FunctionParametersLibrary", "FunctionOutputLibrary"):
            n = db_query(DB_AGENTIC, f"SELECT COUNT(*) AS n FROM {tbl}")[0]["n"]
            print(f"  {tbl:30s} {n:>3} rows")
    """),
    py("""
        # Have a look at the strategies you just seeded.
        rows = db_query(DB_AGENTIC, '''
            SELECT StrategyID, StrategyName, StrategyTarget,
                   substr(StrategyDescription, 1, 60) AS description
            FROM StrategyLibrary ORDER BY StrategyID
        ''')
        for r in rows:
            print(f"  [{r['StrategyID']}] {r['StrategyName']:30s} {r['StrategyTarget']:10s} {r['description']}")
    """),

    md("""
        ### How a strategy decomposes into function calls

        Pick `DIRECT SPECIFICATION LOOKUP`. Its `PlanSteps` is the comma-
        separated string `Extract Product Number, Query Database, Extract Attributes, Analyze With LLM`.
        The planner parses that into a sequence of function calls:

        ```mermaid
        flowchart LR
            Q([User query]) --> EPN[Extract Product Number]
            EPN -->|Keyword Output| QDB[Query Database]
            QDB -->|items| EA[Extract Attributes]
            EA -->|extracted_data| ANA[Analyze With LLM]
            ANA --> A([Final answer])
        ```

        Each arrow is data flowing through `FunctionOutputInSession` — one
        function's output becomes the next function's input slot. Slot
        names are declared in `OUTPUTS_SEED` / `PARAMS_SEED` (§4 above).
    """),
    md("""
        ### 🛠 Try it — peek at any strategy's plan
    """),
    py("""
        # Try it: change PICK to any name from the table above.
        PICK = "MULTI-PRODUCT COMPARISON"

        plan = db_query(DB_AGENTIC,
            "SELECT PlanSteps FROM StrategyLibrary WHERE StrategyName = ?", (PICK,))
        if plan:
            steps = [s.strip() for s in plan[0]["PlanSteps"].split(",")]
            print(f"{PICK} →")
            for i, step in enumerate(steps, 1):
                print(f"   {i}. {step}")
        else:
            print(f"no strategy named {PICK!r}")
    """),

    md("""
        # §5. The session state

        A query enters the workflow as a `SessionState` dict — every node
        reads and writes fields on it. Below is a `TypedDict` matching the
        production project's shape.

        Only a few fields really matter on first read: `query`, `currentGoalID`,
        `currentStrategyID`, `currentFunctionID`, the three `*Satisfied`
        booleans, `judgeConfidence`, and `finalAnswer`. The rest are
        bookkeeping for tri-condition routing.
    """),
    py("""
        class SessionState(TypedDict, total=False):
            # ---- core session ----
            query: str
            sessionID: int

            # ---- current execution context ----
            currentGoalID: Optional[int]
            currentStrategyID: Optional[int]
            currentFunctionID: Optional[int]

            # ---- completion / routing flags ----
            strategySatisfied: bool
            goalSatisfied: bool
            strategyAborted: bool
            workflowComplete: bool

            # ---- final results ----
            judgeConfidence: Optional[float]
            finalAnswer: Optional[str]

            # ---- debug knob: bypass LLM strategy selection ----
            forcedStrategy: Optional[str]


        def make_session_state(query: str, *, forced_strategy: Optional[str] = None) -> SessionState:
            \"\"\"Initial state for a new query.\"\"\"
            return {
                "query": query,
                "sessionID": int(time.time() * 1000) % 1_000_000,
                "currentGoalID": None,
                "currentStrategyID": None,
                "currentFunctionID": None,
                "strategySatisfied": False,
                "goalSatisfied": False,
                "strategyAborted": False,
                "workflowComplete": False,
                "judgeConfidence": None,
                "finalAnswer": None,
                "forcedStrategy": forced_strategy,
            }


        # Field meta — used by the rich printer below to label what each field does.
        STATE_FIELDS: List[Tuple[str, str]] = [
            ("query",              "the user's question (input)"),
            ("sessionID",          "unique per run, scopes session tables"),
            ("currentGoalID",      "→ GoalInSession row"),
            ("currentStrategyID",  "→ StrategyInSession row"),
            ("currentFunctionID",  "→ FunctionInSession row"),
            ("strategySatisfied",  "current strategy finished (success or abort)"),
            ("goalSatisfied",      "judge approved an answer"),
            ("strategyAborted",    "current strategy failed → re-plan"),
            ("workflowComplete",   "all strategies tried OR success"),
            ("judgeConfidence",    "0.0–1.0 from goal_validation"),
            ("finalAnswer",        "synthesised text once goal is satisfied"),
            ("forcedStrategy",     "debug knob: bypass LLM strategy selection"),
        ]


        def show_state(state: SessionState) -> None:
            \"\"\"Pretty-print the current SessionState — green for set, dim for None.\"\"\"
            try:
                from IPython.display import display, HTML
                rows = []
                for k, desc in STATE_FIELDS:
                    v = state.get(k)
                    is_set = v not in (None, False, "", [], {})
                    color = "#0a7d32" if is_set else "#888"
                    val = "—" if v is None else (
                        "True" if v is True else ("False" if v is False else str(v)))
                    if len(val) > 60: val = val[:57] + "…"
                    rows.append(
                        f"<tr style='border-bottom:1px solid #eee'>"
                        f"<td style='padding:3px 8px;font-family:monospace'>{k}</td>"
                        f"<td style='padding:3px 8px;color:{color};font-family:monospace'>{val}</td>"
                        f"<td style='padding:3px 8px;color:#666;font-size:0.9em'>{desc}</td>"
                        f"</tr>"
                    )
                display(HTML(
                    "<table style='border-collapse:collapse'>"
                    "<tr><th style='text-align:left;padding:3px 8px'>field</th>"
                    "<th style='text-align:left;padding:3px 8px'>value</th>"
                    "<th style='text-align:left;padding:3px 8px'>meaning</th></tr>"
                    + "".join(rows) + "</table>"
                ))
            except Exception:                                 # plain-text fallback
                w = max(len(k) for k, _ in STATE_FIELDS) + 2
                for k, desc in STATE_FIELDS:
                    print(f"  {k.ljust(w)} {state.get(k)!r:<30} {desc}")


        # Example
        s = make_session_state("What is the maximum working pressure for hose 1071-00-16?")
        show_state(s)
    """),

    md("""
        # §6. The function library

        Six callable functions, plus the helpers and prompts they need. Each
        function follows the same interface used in the production project:

        ```
        handler(params: dict) -> (success: bool, result: dict | str)
        ```

        - `params` is a dict the planner builds at runtime, populating values
          from the user query (`"Input"` → `query`) or from previously-stored
          outputs (empty string → merge from `FunctionOutputInSession`).
        - On success, `result` is a dict whose keys are the **declared outputs**
          for that function (see `OUTPUTS_SEED` in §4). The executor stores
          each one in `FunctionOutputInSession`.

        The next several cells define helpers, prompts, then the six
        functions, then a registry that maps name → callable.
    """),
    md("""
        ### LLM helper — one POST to Ollama

        > **Simplified:** The production project uses `langchain_ollama.ChatOllama`
        > with three configured tiers (`basic` / `reasoning` / `multimodal`),
        > a retry policy with exponential backoff, and a 15-second special-case
        > pause when the runner crashes. We bypass all of that — one
        > `requests.post` call, no retries — so the friend only needs `requests`
        > installed alongside `langgraph`.
    """),
    py("""
        def ollama_chat(messages: List[Dict[str, str]], temperature: float = 0.0,
                        model: str = OLLAMA_MODEL) -> str:
            \"\"\"POST /api/chat → return content string. No retries — keep it readable.\"\"\"
            r = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": model, "messages": messages,
                      "stream": False, "options": {"temperature": temperature}},
                timeout=180,
            )
            r.raise_for_status()
            return r.json()["message"]["content"]


        # smoke
        print(ollama_chat([{"role": "user", "content": "Say only the word: ok"}]).strip())
    """),
    md("""
        ### Prompts (lifted from `Layer_2_Agentic_Reasoning/config/prompts.yaml`)

        Inlined here so the friend has the entire prompt text in front of
        them. Tighten or rewrite as you experiment.
    """),
    py("""
        PROMPTS = {
            "goal_definition": {
                "system":
                    "You are a goal definition assistant for technical queries about industrial products.\\n"
                    "Analyze a user query and extract key information that helps validate later answers.\\n"
                    "Respond with valid JSON only — no preamble.\\n\\n"
                    "Required JSON format:\\n"
                    "{\\n"
                    '  "goal_description": "TEXT",\\n'
                    '  "expected_content_types": ["product_specs", "lookup_values", "..."],\\n'
                    '  "key_terms": ["pressure", "temperature", "..."],\\n'
                    '  "success_indicators": ["specific value with units", "source citation", "..."]\\n'
                    "}",
                "user": "USER QUERY: {query}\\n\\nAnalyze this query and define the goal.",
            },

            "strategy_selection": {
                "system":
                    "You are a strategy-planning assistant for a technical documentation system.\\n\\n"
                    "CRITICAL RULES:\\n"
                    "• Choose EXACTLY ONE strategy from the AVAILABLE STRATEGIES list.\\n"
                    "• Use the EXACT strategy name as written (case-sensitive).\\n"
                    "• You CANNOT choose any from STRATEGIES ALREADY EXECUTED.\\n"
                    "• You CANNOT invent strategy names.\\n\\n"
                    "Required JSON format:\\n"
                    '{"StrategyName": "[EXACT name]", "Rationale": "Brief reason"}',
                "user":
                    "USER QUERY: {query}\\n"
                    "GOAL: {goal_desc}\\n\\n"
                    "STRATEGIES ALREADY EXECUTED (forbidden):\\n{tried}\\n\\n"
                    "AVAILABLE STRATEGIES (choose exactly one):\\n{available}\\n\\n"
                    "Return ONLY valid JSON.",
            },

            "product_code_extraction": {
                "system":
                    "You extract COMPLETE product codes from a user query.\\n"
                    "Preserve every digit and suffix exactly. Output ONLY the codes,\\n"
                    "comma-separated if multiple. Output empty string if none found.\\n"
                    "Examples: '1071-00-16' → '1071-00-16'  |  'hose 4201-16-16' → '4201-16-16'",
                "user": "Query: {query}\\nProduct codes:",
            },

            "extract_requirements": {
                "system":
                    "You extract structured requirements from a user query about hydraulic hoses or couplings.\\n"
                    "Return JSON only. Leave fields null if not mentioned.\\n\\n"
                    "Schema:\\n"
                    "{\\n"
                    '  "application": "hydraulic|water|steam|chemical|...|null",\\n'
                    '  "pressure_max_bar": <number|null>,\\n'
                    '  "temperature_max_c": <number|null>,\\n'
                    '  "diameter_mm": <number|null>,\\n'
                    '  "keywords": ["term", "term", ...],\\n'
                    '  "summary": "1-sentence intent"\\n'
                    "}",
                "user": "Query: {query}\\nReturn JSON:",
            },

            "analyze_with_llm": {
                "system":
                    "You are a technical analyst for industrial hose and coupling products.\\n"
                    "Use ONLY the provided product data — no external knowledge.\\n"
                    "Answer in 1–2 sentences. Include exact values with units. "
                    "Cite product_code or family_name. If the data is missing, say so plainly.\\n"
                    "Match the language of the user's question (Swedish in → Swedish out).",
                "user":
                    "PRODUCT DATA:\\n{context}\\n\\n"
                    "QUESTION: {question}\\n\\n"
                    "Answer using only the data above:",
            },

            "goal_validation": {
                "system":
                    "You evaluate whether the analysis output answers the user's query.\\n"
                    "Respond with ONLY one JSON object: {\\\"confidence\\\": <0.0..1.0>}.\\n"
                    "No prose, no markdown.\\n\\n"
                    "Scoring:\\n"
                    "  0.8–1.0  complete answer with specific values\\n"
                    "  0.6–0.7  good but missing some details\\n"
                    "  0.3–0.5  partial / insufficient\\n"
                    "  0.0–0.2  off-topic or no answer\\n"
                    "If you cannot produce valid JSON, output exactly: {\\\"confidence\\\": 0.0}",
                "user":
                    "USER QUERY:\\n{query}\\n\\n"
                    "GOAL DEFINITION:\\n{goal_definition}\\n\\n"
                    "ANALYSIS OUTPUT:\\n{evidence}\\n\\n"
                    "Required JSON: {{\\\"confidence\\\": 0.0..1.0}}",
            },
        }


        def fmt_prompt(name: str, **kwargs) -> List[Dict[str, str]]:
            \"\"\"Build a [system, user] message list for the named prompt.\"\"\"
            tpl = PROMPTS[name]
            return [
                {"role": "system", "content": tpl["system"]},
                {"role": "user",   "content": tpl["user"].format(**kwargs)},
            ]


        def parse_json_response(text: str) -> Optional[dict]:
            \"\"\"Pull a JSON object out of a noisy LLM response.\"\"\"
            text = text.strip()
            # Strip ```json fences if present.
            text = re.sub(r"^```(?:json)?\\s*", "", text)
            text = re.sub(r"\\s*```$", "", text)
            try:
                return json.loads(text)
            except Exception:
                pass
            m = re.search(r"\\{.*\\}", text, flags=re.S)
            if m:
                try:
                    return json.loads(m.group())
                except Exception:
                    return None
            return None
    """),

    md("""
        ### Function: **Extract Product Number**

        Pulls product codes out of the user query via LLM. Output goes into
        `Keyword Output` (the canonical name from the production project) so
        downstream functions like `Query Database` can pick it up.
    """),
    py("""
        def func_extract_product_number(params: Dict[str, Any]) -> Tuple[bool, dict]:
            # Slot "Input" carries the user query (set by the planner at runtime).
            query = params.get("Input", "") or ""

            # Single LLM call — see PROMPTS['product_code_extraction'] for the prompt.
            out = ollama_chat(fmt_prompt("product_code_extraction", query=query))

            # Robustness: take just the first line, strip a leading "Product codes:" if present.
            codes = out.strip().splitlines()[0] if out.strip() else ""
            codes = re.sub(r"^[Pp]roduct codes?:\\s*", "", codes).strip().strip('"').strip("'")

            # Output slot name MUST match what's declared in OUTPUTS_SEED for this function.
            return True, {"Keyword Output": codes}
    """),
    md("""
        ### 🛠 Try it — one function in isolation

        Each handler takes a `params` dict and returns `(success, dict)`.
        That's it. The rest of the framework just plumbs the right values
        in and out of those dicts. Testing one in isolation is straightforward.
    """),
    py("""
        ok, result = func_extract_product_number({"Input": "What is the working pressure of hose 1071-00-16 vs 4201-16-16?"})
        print("ok    :", ok)
        print("result:", result)
    """),

    md("""
        ### Function: **Extract Requirements**

        Same idea but for application / pressure / temperature / etc.
        Returns a structured `requirements` dict.
    """),
    py("""
        def func_extract_requirements(params: Dict[str, Any]) -> Tuple[bool, dict]:
            query = params.get("Input", "") or ""
            out = ollama_chat(fmt_prompt("extract_requirements", query=query))
            data = parse_json_response(out) or {"summary": "(parse failed)", "keywords": []}
            return True, {"requirements": data}
    """),

    md("""
        ### Function: **Query Database**

        Looks up products by code(s). The codes can come from the user
        query directly, or via `Extract Product Number` upstream
        (the planner merges these via the `Keyword Output` slot).
    """),
    py("""
        def _split_codes(s: str) -> List[str]:
            \"\"\"Split a 'A, B; C\\nD' style string into clean codes.\"\"\"
            if not s:
                return []
            return [p.strip() for p in re.split(r"[,;\\n]+", s) if p.strip()]


        def func_query_database(params: Dict[str, Any]) -> Tuple[bool, dict]:
            codes = _split_codes(params.get("Keyword Output", "") or "")
            if not codes:
                return False, "no product codes provided"

            placeholders = ",".join("?" for _ in codes)
            sql = f'''
                SELECT p.product_code, p.variant_suffix, p.specifications,
                       p.page_number, pf.family_code, pf.name AS family_name,
                       pf.description AS family_description, pf.applications,
                       pf.construction_details
                FROM products p
                JOIN product_families pf ON pf.id = p.family_id
                WHERE p.product_code IN ({placeholders})
            '''
            items = db_query(DB_HARVESTED, sql, tuple(codes))

            # Parse the JSON spec blob so downstream Extract Attributes sees a dict.
            for it in items:
                spec = it.get("specifications")
                if isinstance(spec, str):
                    try:
                        it["specifications"] = json.loads(spec)
                    except Exception:
                        pass

            return True, {"items": items, "count": len(items)}
    """),

    md("""
        ### Function: **Search Products**

        Keyword search across families and their applications text. Used
        when the query doesn't mention a specific code.

        > **Simplified:** The production version of this function uses
        > ChromaDB embeddings (`nomic-embed-text`) for semantic similarity,
        > then re-ranks. We use plain SQL `LIKE` so the friend doesn't need
        > to install ChromaDB or pull the embedding model — at the cost of
        > worse recall on synonyms / paraphrases.
    """),
    py("""
        def func_search_products(params: Dict[str, Any]) -> Tuple[bool, dict]:
            keywords = params.get("keywords", "") or ""
            limit = int(params.get("limit", 20) or 20)

            # Tokenize the user's text. We score families that contain MORE tokens.
            tokens = [t for t in re.split(r"\\W+", keywords.lower()) if len(t) > 2]
            if not tokens:
                return False, "no usable keywords"

            # Crude but effective: AND-of-LIKE on applications + description.
            where = " AND ".join(
                "(LOWER(applications) LIKE ? OR LOWER(description) LIKE ? OR LOWER(name) LIKE ?)"
                for _ in tokens
            )
            args: list = []
            for t in tokens:
                args.extend([f"%{t}%", f"%{t}%", f"%{t}%"])
            args.append(limit)

            items = db_query(DB_HARVESTED, f'''
                SELECT family_code, name, description, applications, page_number
                FROM product_families WHERE {where}
                ORDER BY family_code LIMIT ?
            ''', tuple(args))

            return True, {"items": items, "count": len(items)}
    """),

    md("""
        ### Function: **Search Families**
    """),
    py("""
        def func_search_families(params: Dict[str, Any]) -> Tuple[bool, dict]:
            keywords = params.get("keywords", "") or ""
            limit = int(params.get("limit", 20) or 20)

            # Try exact family_code first.
            code_match = re.search(r"\\b(\\d{4}(?:-\\d+)?)\\b", keywords)
            if code_match:
                items = db_query(DB_HARVESTED, '''
                    SELECT family_code, name, subtitle, description, applications,
                           construction_details, page_number
                    FROM product_families WHERE family_code = ? LIMIT ?
                ''', (code_match.group(1), limit))
                if items:
                    return True, {"items": items, "count": len(items)}

            # Fall back to LIKE on name / description.
            items = db_query(DB_HARVESTED, '''
                SELECT family_code, name, subtitle, description, applications,
                       construction_details, page_number
                FROM product_families
                WHERE LOWER(name) LIKE ? OR LOWER(description) LIKE ?
                ORDER BY family_code LIMIT ?
            ''', (f"%{keywords.lower()}%", f"%{keywords.lower()}%", limit))

            return True, {"items": items, "count": len(items)}
    """),

    md("""
        ### Function: **Extract Attributes** (deterministic, no LLM)

        Takes whatever `items` the previous function produced and flattens
        each one into a list of `(label, value, source_field)` tuples. This
        is what `Analyze With LLM` consumes as `extracted_data`.
    """),
    py("""
        # Field-label aliases (truncated subset of the production glossary).
        FIELD_LABELS = {
            "spec_arb_tr__mpa": "Working pressure (MPa)",
            "spec_arb_tr__bar": "Working pressure (bar)",
            "spec_id_mm":       "Inner diameter (mm)",
            "spec_yd_mm":       "Outer diameter (mm)",
            "spec_temperatur":  "Temperature range",
            "spec_vikt_kg_m":   "Weight (kg/m)",
            "spec_b_jningsradie_mm": "Min bend radius (mm)",
        }


        def func_extract_attributes(params: Dict[str, Any]) -> Tuple[bool, dict]:
            items = params.get("items")
            # Items may have come through as JSON string from prior storage.
            if isinstance(items, str):
                try:
                    items = json.loads(items)
                except Exception:
                    items = []
            if not isinstance(items, list):
                items = [items] if items else []

            extracted: List[dict] = []
            for it in items[:10]:                              # cap to keep prompts small
                if not isinstance(it, dict):
                    continue
                row = {
                    "product_code":     it.get("product_code"),
                    "family_code":      it.get("family_code"),
                    "family_name":      it.get("family_name") or it.get("name"),
                    "page_number":      it.get("page_number"),
                    "applications":     (it.get("applications") or "")[:300],
                    "construction":     (it.get("construction_details") or "")[:300],
                    "specs": [],
                }
                spec = it.get("specifications")
                if isinstance(spec, dict):
                    for k, v in spec.items():
                        label = FIELD_LABELS.get(k, k)
                        row["specs"].append({"label": label, "value": v, "raw_field": k})
                extracted.append(row)

            return True, {"extracted_data": extracted}
    """),

    md("""
        ### Function: **Analyze With LLM** (final synthesis)

        The terminal function in every strategy. Feeds collected evidence to
        the LLM with the answer-formatting prompt. Output goes to
        `Analysis`, which the workflow promotes to `finalAnswer`.
    """),
    py("""
        def func_analyze_with_llm(params: Dict[str, Any]) -> Tuple[bool, dict]:
            question = params.get("question") or ""
            extracted = params.get("extracted_data")
            assembled = params.get("Assembled Data")

            # Either of the two upstream slots may carry the data.
            ctx_obj = extracted or assembled
            if isinstance(ctx_obj, str):
                try:
                    ctx_obj = json.loads(ctx_obj)
                except Exception:
                    pass

            context = json.dumps(ctx_obj, indent=2, ensure_ascii=False, default=str)
            if len(context) > 6000:
                context = context[:6000] + "\\n…[truncated]"

            answer = ollama_chat(
                fmt_prompt("analyze_with_llm", context=context, question=question),
                temperature=0.1,
            )
            return True, {"Analysis": answer.strip()}


        # ----- Registry -----
        FUNCTION_MAP: Dict[str, Callable[[Dict[str, Any]], Tuple[bool, Any]]] = {
            "Extract Product Number": func_extract_product_number,
            "Extract Requirements":   func_extract_requirements,
            "Query Database":         func_query_database,
            "Search Products":        func_search_products,
            "Search Families":        func_search_families,
            "Extract Attributes":     func_extract_attributes,
            "Analyze With LLM":       func_analyze_with_llm,
        }
        print("Functions registered:", ", ".join(FUNCTION_MAP))
    """),

    md("""
        # §7. Workflow nodes — the LangGraph state machine

        Seven nodes mirroring the production project's
        `Layer_2_Agentic_Reasoning/logic/workflow_nodes.py`:

        | Node | Purpose |
        |------|---------|
        | `GoalDefine`        | Persist the goal in `GoalInSession`, capture goal-definition metadata |
        | `StrategyPlan`      | Pick a strategy (LLM or `forcedStrategy`), instantiate it + its functions |
        | `FunctionExecute`   | Run the next pending function via `FUNCTION_MAP` |
        | `FunctionValidate`  | Sanity-check the function's outputs |
        | `StrategyValidate`  | Tri-condition routing: continue / abort / succeed |
        | `GoalValidate`      | LLM judge — sets `finalAnswer` if confidence ≥ 0.5 |
        | `done`              | Terminal node |
    """),
    md("""
        ### Helpers used across nodes

        > **Simplified:** These few short functions replace the production
        > `DatabaseManager` (1233 lines, dozens of methods) and
        > `workflow_helpers.py` (343 lines). Same idea — read/write the
        > session tables — fewer abstractions.
    """),
    py("""
        # ---- session-level DB helpers (replaces DatabaseManager) ----------

        def db_exec(sql: str, params: tuple = ()) -> Optional[int]:
            \"\"\"Run a write against agentic.db; return lastrowid for inserts.\"\"\"
            with sqlite3.connect(DB_AGENTIC) as con:
                cur = con.execute(sql, params)
                con.commit()
                return cur.lastrowid


        def create_goal(session_id: int, description: str, target: str) -> int:
            return db_exec(
                "INSERT INTO GoalInSession "
                "(SessionID, GoalName, GoalTarget, GoalDescription) VALUES (?, ?, ?, ?)",
                (session_id, "MainGoal", target, description),
            ) or 0


        def create_strategy(goal_id: int, name: str, plan: str) -> int:
            row = db_query(DB_AGENTIC,
                "SELECT StrategyTarget, StrategyDescription FROM StrategyLibrary "
                "WHERE StrategyName = ?", (name,))
            target = row[0]["StrategyTarget"] if row else ""
            desc   = row[0]["StrategyDescription"] if row else ""
            return db_exec(
                "INSERT INTO StrategyInSession "
                "(GoalID, StrategyName, StrategyTarget, StrategyDescription, PlanSteps) "
                "VALUES (?, ?, ?, ?, ?)",
                (goal_id, name, target, desc, plan),
            ) or 0


        def create_strategy_functions(strategy_id: int, strategy_name: str, plan_steps: str) -> None:
            \"\"\"Insert one FunctionInSession row per function name in the plan.
            Then copy the parameter templates into FunctionParametersInSession.\"\"\"
            for step in [s.strip() for s in plan_steps.split(",")]:
                fid = db_exec(
                    "INSERT INTO FunctionInSession "
                    "(StrategyID, StrategyName, FunctionName) VALUES (?, ?, ?)",
                    (strategy_id, strategy_name, step),
                ) or 0
                # Copy parameter templates.
                templates = db_query(DB_AGENTIC, '''
                    SELECT pl.ParameterName, pl.ParameterValue, pl.Type
                    FROM FunctionParametersLibrary pl
                    JOIN FunctionTemplateLibrary fl ON fl.FunctionTemplateID = pl.FunctionTemplateID
                    WHERE fl.FunctionName = ?
                ''', (step,))
                for t in templates:
                    db_exec(
                        "INSERT INTO FunctionParametersInSession "
                        "(FunctionID, FunctionName, StrategyName, ParameterName, ParameterValue, Type) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (fid, step, strategy_name,
                         t["ParameterName"], t["ParameterValue"], t["Type"]),
                    )


        def get_current_function_id(strategy_id: int) -> Optional[int]:
            \"\"\"Next pending function (FunctionSuccess IS NULL).\"\"\"
            rows = db_query(DB_AGENTIC,
                "SELECT FunctionID FROM FunctionInSession "
                "WHERE StrategyID = ? AND FunctionSuccess IS NULL "
                "ORDER BY FunctionID LIMIT 1", (strategy_id,))
            return rows[0]["FunctionID"] if rows else None


        def collect_outputs(strategy_id: int, output_name: str) -> List[Any]:
            \"\"\"Gather all stored outputs of a given name from earlier functions in this strategy.\"\"\"
            rows = db_query(DB_AGENTIC, '''
                SELECT o.OutputValue, o.Type
                FROM FunctionOutputInSession o
                JOIN FunctionInSession f ON f.FunctionID = o.FunctionID
                WHERE f.StrategyID = ? AND o.OutputName = ?
                ORDER BY o.FunctionOutputID
            ''', (strategy_id, output_name))
            out: List[Any] = []
            for r in rows:
                v = r["OutputValue"]
                if r["Type"] == "json":
                    try:
                        v = json.loads(v)
                    except Exception:
                        pass
                out.append(v)
            return out


        def merge_values(name: str, values: List[Any]) -> Any:
            if not values:
                return ""
            if len(values) == 1:
                return values[0]
            # If all dicts/lists, concatenate.
            if all(isinstance(v, list) for v in values):
                merged: list = []
                for v in values:
                    merged.extend(v)
                return merged
            # Otherwise comma-join strings.
            return ", ".join(str(v) for v in values)


        def tried_strategies(goal_id: int) -> List[str]:
            return [r["StrategyName"] for r in db_query(DB_AGENTIC,
                "SELECT DISTINCT StrategyName FROM StrategyInSession WHERE GoalID = ?", (goal_id,))]


        VERBOSE = True

        def trace(label: str, msg: str) -> None:
            if VERBOSE:
                print(f"  [{label}] {msg}")
    """),

    md("""
        ### `node_goal_define` — capture the goal
    """),
    py("""
        def node_goal_define(state: SessionState) -> SessionState:
            sess  = state["sessionID"]
            query = state["query"].strip()
            goal_resp = ollama_chat(fmt_prompt("goal_definition", query=query))
            data = parse_json_response(goal_resp) or {}
            description = data.get("goal_description") or f"Answer: {query.rstrip('?.!')}"
            target = " ".join(query.split()[:4])
            gid = create_goal(sess, description, target)
            trace("GoalDefine", f"goal {gid}: {description}")
            state["currentGoalID"] = gid
            return state
    """),

    md("""
        ### `node_strategy_plan` — pick (or terminate)
    """),
    py("""
        def node_strategy_plan(state: SessionState) -> SessionState:
            gid   = state["currentGoalID"]
            query = state["query"]

            tried = tried_strategies(gid)
            available = [s["StrategyName"] for s in db_query(DB_AGENTIC,
                "SELECT StrategyName FROM StrategyLibrary ORDER BY StrategyID")
                if s["StrategyName"] not in tried]

            if not available:
                trace("StrategyPlan", f"all strategies exhausted; tried={tried}")
                state["workflowComplete"] = True
                state["goalSatisfied"] = False
                if not state.get("finalAnswer"):
                    state["finalAnswer"] = "All strategies exhausted; no satisfactory answer."
                return state

            # ---- choose strategy: forced or LLM ----
            forced = state.get("forcedStrategy")
            sname: Optional[str] = None
            if forced and forced in available:
                sname = forced
                trace("StrategyPlan", f"forced: {sname}")
            else:
                resp = ollama_chat(fmt_prompt(
                    "strategy_selection",
                    query=query,
                    goal_desc=db_query(DB_AGENTIC,
                        "SELECT GoalDescription FROM GoalInSession WHERE GoalID = ?", (gid,))[0]["GoalDescription"],
                    tried="\\n".join(f"- {t}" for t in tried) or "- None",
                    available="\\n".join(f"- {a}" for a in available),
                ))
                payload = parse_json_response(resp) or {}
                cand = (payload.get("StrategyName") or payload.get("strategy_name") or "").strip()
                if cand in available:
                    sname = cand
                else:
                    sname = available[0]                    # safety fallback
                    trace("StrategyPlan", f"LLM said {cand!r}, not in available; falling back to {sname}")

            row = db_query(DB_AGENTIC,
                "SELECT PlanSteps FROM StrategyLibrary WHERE StrategyName = ?", (sname,))
            plan_steps = row[0]["PlanSteps"]
            trace("StrategyPlan", f"chose {sname}: {plan_steps}")

            sid = create_strategy(gid, sname, plan_steps)
            create_strategy_functions(sid, sname, plan_steps)
            first_fid = get_current_function_id(sid)

            state.update({
                "currentStrategyID": sid,
                "currentFunctionID": first_fid,
                "strategySatisfied": False,
                "strategyAborted": False,
            })
            return state
    """),

    md("""
        ### `node_function_execute` — resolve params, dispatch, store outputs

        Five clearly-labelled stages in the cell below:

        1. **Look up** which function we're running (from `FunctionInSession`).
        2. **Resolve parameters**: each row in `FunctionParametersInSession`
           tells us where a value comes from — the user query (`"Input"`),
           a prior function's output (empty string), or a literal template value.
        3. **Dispatch** to the registered handler in `FUNCTION_MAP`.
        4. **Persist** the success flag and any failure text.
        5. **Store outputs** that match the declared output schema; promote
           `Analyze With LLM`'s `Analysis` to the user-visible `finalAnswer`.
    """),
    py("""
        def node_function_execute(state: SessionState) -> SessionState:
            # Guard: don't execute if a previous step already aborted the strategy.
            if state.get("strategyAborted"):
                return state

            fid   = state["currentFunctionID"]
            query = state["query"]

            # ─── 1. Look up the function row ─────────────────────────────
            row = db_query(DB_AGENTIC,
                "SELECT FunctionName, StrategyID, StrategyName "
                "FROM FunctionInSession WHERE FunctionID = ?", (fid,))
            if not row:
                trace("FunctionExecute", f"no function with id {fid}; aborting")
                state["strategyAborted"] = True
                return state
            fn, sid, sname = row[0]["FunctionName"], row[0]["StrategyID"], row[0]["StrategyName"]

            # ─── 2. Resolve parameters ───────────────────────────────────
            # ParameterValue conventions:
            #   "Input"  → use the user query as the value
            #   ""       → merge values from prior FunctionOutputInSession rows
            #              that share this strategy and parameter name
            #   anything → literal template value (parsed by Type)
            param_rows = db_query(DB_AGENTIC,
                "SELECT ParameterName, ParameterValue, Type FROM FunctionParametersInSession "
                "WHERE FunctionID = ?", (fid,))
            params: Dict[str, Any] = {}
            for p in param_rows:
                name, val, ptype = p["ParameterName"], p["ParameterValue"], p["Type"]
                if val == "Input":
                    params[name] = query
                elif val == "":
                    merged = collect_outputs(sid, name)
                    if not merged and name == "Input":
                        merged = [query]                            # first-function fallback
                    params[name] = merge_values(name, merged) if merged else ""
                else:
                    # Literal template value — coerce by declared type.
                    if ptype == "json":
                        try:    params[name] = json.loads(val)
                        except: params[name] = val
                    elif ptype == "integer":
                        try:    params[name] = int(val)
                        except: params[name] = val
                    else:
                        params[name] = val

            trace("FunctionExecute", f"{fn}({list(params)})")

            # ─── 3. Dispatch via FUNCTION_MAP ────────────────────────────
            handler = FUNCTION_MAP.get(fn)
            if not handler:
                trace("FunctionExecute", f"no handler for {fn!r}; aborting")
                state["strategyAborted"] = True
                db_exec("UPDATE FunctionInSession SET FunctionSuccess = 0, failedtext = ? "
                        "WHERE FunctionID = ?", (f"no handler for {fn}", fid))
                return state

            try:
                success, result = handler(params)
            except Exception as e:
                trace("FunctionExecute", f"{fn} raised: {e}")
                success, result = False, str(e)

            # ─── 4. Record success / failure ─────────────────────────────
            db_exec("UPDATE FunctionInSession SET FunctionSuccess = ?, failedtext = ? "
                    "WHERE FunctionID = ?",
                    (1 if success else 0,
                     "" if success else str(result)[:500], fid))

            # ─── 5. Persist outputs + promote to finalAnswer ─────────────
            if success and isinstance(result, dict):
                # Only store outputs declared in the function's output schema (§4).
                declared = {n for (n, _, _) in OUTPUTS_SEED.get(fn, [])}
                for oname, oval in result.items():
                    if oname not in declared:
                        continue
                    if isinstance(oval, (list, dict)):
                        sval, otype = json.dumps(oval, ensure_ascii=False), "json"
                    else:
                        sval, otype = str(oval), "string"
                    db_exec("INSERT INTO FunctionOutputInSession "
                            "(FunctionID, FunctionName, StrategyName, OutputName, OutputValue, Type) "
                            "VALUES (?, ?, ?, ?, ?, ?)",
                            (fid, fn, sname, oname, sval, otype))

                # Bubble the analyzer's text up so the trace shows it immediately.
                if fn == "Analyze With LLM":
                    state["finalAnswer"] = result.get("Analysis", state.get("finalAnswer"))
            else:
                state["strategyAborted"] = True
                trace("FunctionExecute", f"{fn} failed → strategy aborted")

            return state
    """),

    md("""
        ### `node_function_validate` — minimal output sanity
    """),
    py("""
        def node_function_validate(state: SessionState) -> SessionState:
            fid = state["currentFunctionID"]
            row = db_query(DB_AGENTIC,
                "SELECT FunctionSuccess, FunctionName FROM FunctionInSession WHERE FunctionID = ?",
                (fid,))
            if not row or row[0]["FunctionSuccess"] != 1:
                state["strategyAborted"] = True
                return state

            outs = db_query(DB_AGENTIC,
                "SELECT OutputName, OutputValue FROM FunctionOutputInSession WHERE FunctionID = ?",
                (fid,))
            if not outs:
                trace("FunctionValidate", f"{row[0]['FunctionName']} produced no outputs")
                state["strategyAborted"] = True
            return state
    """),

    md("""
        ### `node_strategy_validate` — tri-condition routing

        This is the load-bearing node. It looks at the strategy's function rows and decides:
        - any failed → **abort** → re-plan
        - all done   → **succeed** → goal validation
        - more pending → **continue** → next function
    """),
    py("""
        def node_strategy_validate(state: SessionState) -> SessionState:
            sid = state["currentStrategyID"]
            stats = db_query(DB_AGENTIC, '''
                SELECT
                  COUNT(*)                                   AS total,
                  SUM(CASE WHEN FunctionSuccess = 1 THEN 1 ELSE 0 END) AS succeeded,
                  SUM(CASE WHEN FunctionSuccess = 0 THEN 1 ELSE 0 END) AS failed,
                  SUM(CASE WHEN FunctionSuccess IS NULL THEN 1 ELSE 0 END) AS pending
                FROM FunctionInSession WHERE StrategyID = ?
            ''', (sid,))[0]
            total, succeeded, failed, pending = (stats["total"], stats["succeeded"] or 0,
                                                 stats["failed"] or 0, stats["pending"] or 0)
            trace("StrategyValidate", f"strategy {sid}: {succeeded}/{total} ok, {pending} pending, {failed} failed")

            if failed > 0:
                db_exec("UPDATE StrategyInSession SET StrategySuccess = 0, StrategyValidation = ? "
                        "WHERE StrategyID = ?", (f"{failed} function(s) failed", sid))
                state["strategySatisfied"] = True
                state["strategyAborted"]   = True
                return state

            if pending == 0:
                db_exec("UPDATE StrategyInSession SET StrategySuccess = 1, StrategyValidation = ? "
                        "WHERE StrategyID = ?", ("all functions ok", sid))
                state["strategySatisfied"] = True
                state["strategyAborted"]   = False
                return state

            # still pending — continue
            state["currentFunctionID"] = get_current_function_id(sid)
            state["strategySatisfied"] = False
            state["strategyAborted"]   = False
            return state
    """),

    md("""
        ### `node_goal_validate` — the LLM judge

        The verify-then-summarise gate. We collect the strategy's `Analysis`
        outputs and ask an LLM judge whether they satisfy the original
        query. Confidence ≥ 0.5 → goal satisfied; otherwise re-plan.
    """),
    py("""
        def node_goal_validate(state: SessionState) -> SessionState:
            gid   = state["currentGoalID"]
            query = state["query"]

            # Collect Analysis outputs from any successful strategies under this goal.
            evidence_rows = db_query(DB_AGENTIC, '''
                SELECT o.OutputValue
                FROM FunctionOutputInSession o
                JOIN FunctionInSession f      ON f.FunctionID  = o.FunctionID
                JOIN StrategyInSession  s     ON s.StrategyID  = f.StrategyID
                WHERE s.GoalID = ? AND s.StrategySuccess = 1 AND o.OutputName = 'Analysis'
            ''', (gid,))
            evidence = "\\n\\n---\\n\\n".join(r["OutputValue"] for r in evidence_rows)

            if not evidence:
                trace("GoalValidate", "no Analysis outputs yet")
                state["goalSatisfied"] = False
                state["judgeConfidence"] = 0.0
                return state

            goal_def = db_query(DB_AGENTIC,
                "SELECT GoalDescription FROM GoalInSession WHERE GoalID = ?", (gid,))[0]["GoalDescription"]

            judge_resp = ollama_chat(fmt_prompt(
                "goal_validation",
                query=query, goal_definition=goal_def, evidence=evidence,
            ))
            payload = parse_json_response(judge_resp) or {"confidence": 0.0}
            try:
                conf = float(payload.get("confidence", 0.0))
            except Exception:
                conf = 0.0

            state["judgeConfidence"] = conf
            satisfied = conf >= 0.5
            state["goalSatisfied"] = satisfied
            trace("GoalValidate", f"confidence={conf:.2f} → satisfied={satisfied}")

            if satisfied:
                state["finalAnswer"] = evidence_rows[-1]["OutputValue"]
                state["workflowComplete"] = True
                db_exec("UPDATE GoalInSession SET GoalSuccess = 1 WHERE GoalID = ?", (gid,))
            else:
                # Re-plan: don't mark complete; StrategyPlan will be re-entered.
                state["finalAnswer"] = None
            return state
    """),

    md("""
        ### `node_done` — terminal
    """),
    py("""
        def node_done(state: SessionState) -> SessionState:
            trace("done", f"workflow complete, final answer present: {state.get('finalAnswer') is not None}")
            return state
    """),

    md("""
        # §8. Build the LangGraph state machine

        Same topology as the production project. Three conditional edges
        give us the **tri-condition routing**:

        ```mermaid
        stateDiagram-v2
            [*] --> GoalDefine
            GoalDefine --> StrategyPlan
            StrategyPlan --> FunctionExecute : new strategy
            StrategyPlan --> done : strategies exhausted
            FunctionExecute --> FunctionValidate
            FunctionValidate --> StrategyValidate
            StrategyValidate --> FunctionExecute : continue (more pending)
            StrategyValidate --> StrategyPlan   : abort (any failed)
            StrategyValidate --> GoalValidate   : success (all done)
            GoalValidate --> done : satisfied (judge ≥ 0.5)
            GoalValidate --> StrategyPlan : retry (judge < 0.5)
            done --> [*]
        ```

        Three places routing branches:

        - **`StrategyPlan`** → `done` *or* `FunctionExecute`
          (do we have any strategies left to try?)
        - **`StrategyValidate`** → `FunctionExecute` *or* `StrategyPlan` *or* `GoalValidate`
          (continue the strategy / give up on it / it's complete)
        - **`GoalValidate`** → `done` *or* `StrategyPlan`
          (the judge is happy / try another strategy)

        > **Simplified:** The production graph also handles parallel function
        > batches (the `[Func1 || Func2]` syntax in `PlanSteps`). The build
        > below treats every plan step as sequential — a parallel group token
        > would be passed to `FUNCTION_MAP` as a literal name and fail.
        > Adding the parser is a small change in `node_strategy_plan` if you
        > need it.
    """),
    py("""
        def _next_after_strategy_validate(state: SessionState) -> str:
            if state.get("strategySatisfied") and state.get("strategyAborted"):
                return "StrategyPlan"          # re-plan
            if state.get("strategySatisfied"):
                return "GoalValidate"          # success → judge
            return "FunctionExecute"           # continue


        def _next_after_strategy_plan(state: SessionState) -> str:
            return "done" if state.get("workflowComplete") else "FunctionExecute"


        def build_graph():
            builder = StateGraph(state_schema=SessionState)

            for name, fn in (
                ("GoalDefine",       node_goal_define),
                ("StrategyPlan",     node_strategy_plan),
                ("FunctionExecute",  node_function_execute),
                ("FunctionValidate", node_function_validate),
                ("StrategyValidate", node_strategy_validate),
                ("GoalValidate",     node_goal_validate),
                ("done",             node_done),
            ):
                builder.add_node(name, fn)

            builder.set_entry_point("GoalDefine")

            for src, tgt in (
                ("GoalDefine",       "StrategyPlan"),
                ("FunctionExecute",  "FunctionValidate"),
                ("FunctionValidate", "StrategyValidate"),
            ):
                builder.add_edge(src, tgt)

            builder.add_conditional_edges(
                "StrategyValidate", _next_after_strategy_validate,
                {"GoalValidate": "GoalValidate",
                 "StrategyPlan": "StrategyPlan",
                 "FunctionExecute": "FunctionExecute"},
            )
            builder.add_conditional_edges(
                "StrategyPlan", _next_after_strategy_plan,
                {"done": "done", "FunctionExecute": "FunctionExecute"},
            )
            builder.add_conditional_edges(
                "GoalValidate", lambda s: bool(s.get("goalSatisfied")),
                {True: "done", False: "StrategyPlan"},
            )
            builder.add_edge("done", END)

            graph = builder.compile()
            if graph.config is None:
                graph.config = {}
            graph.config["recursion_limit"] = 60        # cap retries per query
            return graph


        graph = build_graph()
        print("graph compiled:", type(graph).__name__)
    """),
    md("""
        ### Render the *actual* compiled graph

        The Mermaid block above is hand-drawn so it stays readable. The cell
        below dumps the **real** topology straight from LangGraph. They
        should match — if they don't, your edits to `build_graph()` changed
        the shape.
    """),
    py("""
        # Render the compiled graph as Mermaid (renders inline if your renderer supports it).
        try:
            mermaid_src = graph.get_graph().draw_mermaid()
            try:
                from IPython.display import display, Markdown
                display(Markdown("```mermaid\\n" + mermaid_src + "\\n```"))
            except Exception:
                print(mermaid_src)
        except Exception as e:
            print("(draw_mermaid unavailable:", e, ")")
            print("nodes:", list(graph.get_graph().nodes))
    """),

    md("""
        # §9. Run a query, end-to-end — with live tracing

        We use `graph.stream(...)` instead of `graph.invoke(...)` so we can
        watch state evolve **between** nodes instead of just seeing the final
        answer. Each emitted update is `{node_name: state_after_node}`.

        The `run_traced(...)` helper below:

        1. Re-initialises `agentic.db` so each run starts clean.
        2. Streams the graph, prints which node just fired and which state
           fields it touched.
        3. Times each node so you can see where time goes.
        4. Returns the final state for inspection.
    """),
    py("""
        # Build a small icon palette for the trace output.
        NODE_ICONS = {
            "GoalDefine":       "🎯",
            "StrategyPlan":     "🧠",
            "FunctionExecute":  "⚙️ ",
            "FunctionValidate": "🧪",
            "StrategyValidate": "📐",
            "GoalValidate":     "⚖️ ",
            "done":             "🏁",
        }

        # Fields worth highlighting in the per-step trace (the rest is bookkeeping).
        TRACKED = ("currentGoalID", "currentStrategyID", "currentFunctionID",
                   "strategySatisfied", "goalSatisfied", "strategyAborted",
                   "judgeConfidence", "finalAnswer", "workflowComplete")


        def run_traced(query: str, *, forced_strategy: Optional[str] = None,
                       verbose_inner: bool = False) -> SessionState:
            \"\"\"Stream the graph for one query, print per-node trace, return final state.\"\"\"
            global VERBOSE
            saved, VERBOSE = VERBOSE, verbose_inner          # quieten inner trace() calls
            try:
                init_agentic_db(drop_and_recreate=True)
                populate_template_libraries()

                state = make_session_state(query, forced_strategy=forced_strategy)
                last_seen: Dict[str, Any] = dict(state)
                print(f"❓ query: {query}\\n")
                t0 = time.time()
                final: SessionState = state

                for step, update in enumerate(graph.stream(state), start=1):
                    for node_name, partial in update.items():
                        # Compute a diff vs the last full state so we only print what changed.
                        changed = {k: partial.get(k) for k in TRACKED
                                   if k in partial and partial.get(k) != last_seen.get(k)}
                        last_seen.update(partial)
                        final = partial   # last partial is the new full state under LangGraph
                        icon = NODE_ICONS.get(node_name, "•")
                        elapsed = time.time() - t0
                        print(f"  [{step:02d}] {icon} {node_name:18s}  "
                              f"(+{elapsed:5.1f}s)")
                        for k, v in changed.items():
                            sval = repr(v)
                            if len(sval) > 90: sval = sval[:87] + "…"
                            print(f"        ↳ {k:20s} = {sval}")
                print(f"\\n⏱  total: {time.time() - t0:.1f}s")
                return final
            finally:
                VERBOSE = saved


        # Run the happy path.
        final = run_traced("What is the maximum working pressure for hose 1071-00-16?")
    """),
    md("""
        ### State at the end of the run
    """),
    py("""
        show_state(final)
        print("\\nFinal answer:\\n")
        print(final.get("finalAnswer") or "(no answer — judge rejected)")
    """),

    md("""
        ## Forced-strategy debug knob

        Skip the LLM strategy selection by setting `forcedStrategy`. Useful
        when iterating on a single strategy.
    """),
    py("""
        init_agentic_db(drop_and_recreate=True); populate_template_libraries()

        final = run_traced(
            "Tell me about the KAPPAFLEX family.",
            forced_strategy="FAMILY DEEP-DIVE",
        )
        print("\\n📦 final answer:\\n", final.get("finalAnswer"))
    """),

    md("""
        ## Failure mode — verify-then-summarise (the load-bearing demo)

        Ask for something the catalog doesn't contain. What *should* happen:

        1. A strategy runs, retrieves real product data.
        2. `Analyze With LLM` produces *some* synthesised text — but it's
           necessarily speculative, since the answer isn't in the data.
        3. **The judge catches this**: confidence drops below 0.5, so
           `goalSatisfied` stays False.
        4. `node_strategy_plan` re-enters, picks a different strategy, the
           loop repeats. Eventually all strategies are exhausted and the
           workflow terminates with no answer rather than a hallucinated one.

        > 🔍 **Watch in the trace below**: a `judgeConfidence` value below
        > `0.5`, and `finalAnswer` flipping back to `None` after each rejected
        > attempt.

        > **Caveat:** if your local model is too eager to please, the judge
        > may falsely approve. Tighten the prompt in `PROMPTS["goal_validation"]`
        > if you see this — that's the right exercise.
    """),
    py("""
        final = run_traced("What is the warranty period in months for hose 1071-00-16?")

        print("\\n--- Result ---")
        for k in ("judgeConfidence", "goalSatisfied", "workflowComplete", "finalAnswer"):
            print(f"  {k:18s} {final.get(k)}")
    """),

    md("""
        ## Inspecting the persisted execution trace

        Everything the workflow did is in `agentic.db` — ready to query
        for audit, debugging, or further analysis. This is the "Relational
        Control Plane" of the framework's name.
    """),
    py("""
        rows = db_query(DB_AGENTIC, '''
            SELECT s.StrategyID, s.StrategyName, s.StrategySuccess,
                   f.FunctionID, f.FunctionName, f.FunctionSuccess
            FROM StrategyInSession s
            LEFT JOIN FunctionInSession f ON f.StrategyID = s.StrategyID
            ORDER BY s.StrategyID, f.FunctionID
        ''')
        for r in rows:
            ok_s = {1: "✓", 0: "✗", None: "·"}[r["StrategySuccess"]]
            ok_f = {1: "✓", 0: "✗", None: "·"}[r["FunctionSuccess"]]
            print(f"  S{r['StrategyID']:>2} {ok_s} {r['StrategyName']:30s}  "
                  f"F{r['FunctionID'] or 0:>2} {ok_f} {r['FunctionName'] or ''}")
    """),

    md("""
        ## You've finished Layer 2

        You ran a real agentic loop end-to-end:

        - Schema, templates, prompts, function library — all defined in cells you can edit.
        - LangGraph wired with seven nodes and tri-condition routing — same topology as the production project.
        - The judge gates synthesis. Off-catalog queries fail explicitly rather than hallucinating.

        **Where to push next**

        - Add a new strategy or function: extend `STRATEGIES_SEED` / `FUNCTIONS_SEED` and re-run §4.
        - Add semantic search: replace `func_search_products` with a ChromaDB-backed embedding lookup.
        - Add parallel execution: parse `[A \\|\\| B]` syntax in `node_strategy_plan` and dispatch via `concurrent.futures`.
        - Compare strategies side-by-side on the same query by setting `forcedStrategy` per run.

        The full project at [Layer_2_Agentic_Reasoning/](../Layer_2_Agentic_Reasoning/) does all of this and more (15 functions, retry policies, multi-tier LLMs, async).
    """),
]


# =====================================================================
# Notebook 3 — Layer 3: User Interface
# =====================================================================

L3_CELLS: list[dict] = [
    md("""
        # Layer 3 — User Interface
        ### Flask + Server-Sent Events on top of the reasoning engine

        Layer 3 is a thin layer: a Flask app that wraps Layer 2's
        `graph.invoke(...)` and exposes three endpoints —

        | Method | Path                       | Returns                                  |
        |--------|----------------------------|------------------------------------------|
        | POST   | `/query`                   | `{ session_id }`                         |
        | GET    | `/progress/<session_id>`   | text/event-stream of workflow events     |
        | GET    | `/result/<session_id>`     | final structured answer                  |

        plus a single-page UI at `/`.

        We start the Flask app in a **background thread** so the notebook
        can keep running. (If you're editing `web_app.py` itself and want
        Flask's reloader, use `python run_web.py` in a separate terminal
        instead — the threaded server here doesn't reload on file changes.)
    """),
    md("""
        ## 0. Pin project root, probe the environment
    """),
    py("""
        import sys
        sys.path.insert(0, str(__import__("pathlib").Path.cwd()))
        from _helpers import pin_project_root, configure_utf8_stdout, env_probe

        ROOT = pin_project_root()
        configure_utf8_stdout()
        for k, v in env_probe(check_ollama=True).items():
            print(f"{k:30s} {v}")
    """),
    md("""
        ## 1. Inspect the Flask app before starting it

        `web_app.py` initialises the LangGraph workflow on import — that's
        why import alone takes a few seconds. List the routes so you know
        what's actually exposed.
    """),
    py("""
        from Layer_3_User_Interface.web_app import app

        for rule in sorted(app.url_map.iter_rules(), key=lambda r: r.rule):
            methods = ",".join(sorted(rule.methods - {"HEAD", "OPTIONS"}))
            print(f"{methods:8s} {rule.rule}  ->  {rule.endpoint}")
    """),
    py("""
        # Quick peek at the templated frontend (not rendered — just the source).
        from pathlib import Path
        head = Path("Layer_3_User_Interface/templates/index.html").read_text(encoding="utf-8")[:600]
        print(head, "\\n...")
    """),
    md("""
        ## 2. Start the server in a background thread

        We use `werkzeug.serving.make_server` rather than `app.run` so we
        keep an explicit handle to the server and can shut it down cleanly
        from a later cell. Port `5051` is non-default to avoid clashing
        with a separately running `python run_web.py` instance.
    """),
    py("""
        import threading, time
        from werkzeug.serving import make_server

        HOST, PORT = "127.0.0.1", 5051
        BASE_URL   = f"http://{HOST}:{PORT}"

        class _Server(threading.Thread):
            def __init__(self):
                super().__init__(daemon=True)
                self.srv = make_server(HOST, PORT, app)
            def run(self):  self.srv.serve_forever()
            def stop(self): self.srv.shutdown()

        server = _Server()
        server.start()
        time.sleep(1.0)        # give Flask a moment to bind
        print("running at", BASE_URL)
    """),
    py("""
        # Sanity-check: does the index page render?
        import requests
        r = requests.get(BASE_URL, timeout=10)
        print("status:", r.status_code, " | bytes:", len(r.text))
    """),
    md("""
        ## 3. Submit a query over HTTP

        `POST /query` returns a `session_id`. The reasoning workflow
        starts in a background thread inside the Flask app — the response
        is immediate.
    """),
    py("""
        # Try it: change the query string.
        payload = {"query": "What is the maximum working pressure for hose 1071-00-16?"}

        r = requests.post(f"{BASE_URL}/query", json=payload, timeout=10)
        r.raise_for_status()
        session_id = r.json()["session_id"]
        print("session_id:", session_id)
    """),
    md("""
        ## 4. Stream progress events

        `GET /progress/<id>` is a Server-Sent Events stream — one event
        per workflow node transition. We iterate `iter_lines()` and print
        the JSON payloads as they arrive. This is the same trace as
        Notebook 2's `graph.stream(...)`, but going over the wire.
    """),
    py("""
        import json
        from urllib3.exceptions import ProtocolError

        # The stream stays open until the workflow signals completion (or fails).
        # If you want to bail out manually, interrupt the cell.
        try:
            with requests.get(f"{BASE_URL}/progress/{session_id}",
                              stream=True, timeout=120) as resp:
                for raw in resp.iter_lines(decode_unicode=True):
                    if not raw:
                        continue
                    if raw.startswith("data:"):
                        try:
                            evt = json.loads(raw[5:].strip())
                        except json.JSONDecodeError:
                            print("non-json:", raw)
                            continue
                        node = evt.get("node") or evt.get("event") or "?"
                        print(f"[{node}]  ", json.dumps(evt, ensure_ascii=False)[:200])
                        if evt.get("done") or evt.get("complete"):
                            break
        except (requests.exceptions.ChunkedEncodingError, ProtocolError) as e:
            print("(stream closed)", e)
    """),
    md("""
        ## 5. Fetch the final result
    """),
    py("""
        r = requests.get(f"{BASE_URL}/result/{session_id}", timeout=10)
        print("status:", r.status_code)
        try:
            import json
            print(json.dumps(r.json(), indent=2, ensure_ascii=False))
        except Exception:
            print(r.text[:1500])
    """),
    md("""
        ## 6. Use the live UI

        The link below opens the running app in a separate browser window.
        VS Code notebooks generally won't render an `IFrame` to localhost,
        so we don't bother embedding — just click the URL.
    """),
    py("""
        print("Open this in your browser:")
        print(" ", BASE_URL)
    """),
    md("""
        ## 7. Configuration tour

        All Layer 2 settings still apply:

        - **Domain name / description** — `Layer_2_Agentic_Reasoning/config/domain_config.py`
        - **LLM model** — `Layer_2_Agentic_Reasoning/config/config_loader.py`
        - **Debug verbosity** — `Layer_2_Agentic_Reasoning/config/debug_config.py` (0..4)
        - **Flask secret / debug** — `.env` (`SECRET_KEY`, `FLASK_DEBUG`)

        And specifically for Layer 3:

        - The threaded server here does **not** reload on file changes. Iterate
          on `web_app.py` with `python run_web.py` in a separate terminal,
          which uses Werkzeug's reloader.
        - Bind to `127.0.0.1` only from a notebook. Don't expose `0.0.0.0`.
    """),
    md("""
        ## 8. Shut the server down

        Important — leaked threads = leaked port = next run fails to bind.
    """),
    py("""
        server.stop()
        server.join(timeout=3)
        print("server stopped:", not server.is_alive())
    """),
    md("""
        ## You've finished Layer 3

        - The web app is a thin HTTP wrapper around `graph.invoke(...)`.
        - Three endpoints (`/query`, `/progress/<id>`, `/result/<id>`) cover the lifecycle.
        - Background-thread serving keeps the notebook self-contained; switch to a
          standalone `run_web.py` process the moment you start editing `web_app.py`.

        **Going further**

        - For batch evaluation: see `Experiments/Case_I/` (n=100 annotated queries).
        - To adapt this to a new domain (Case II is the worked example): the
          extraction pipeline in Notebook 1 + the strategy/function definitions
          in Layer 2 are the two surfaces you change.
    """),
]


def main() -> None:
    write_nb(HERE / "01_layer1_extraction.ipynb",     L1_CELLS)
    write_nb(HERE / "02_agentic_reasoning.ipynb",     L2_CELLS)
    write_nb(HERE / "03_layer3_user_interface.ipynb", L3_CELLS)

    # Remove the old L2 filename if it still exists from earlier builds.
    old = HERE / "02_layer2_agentic_reasoning.ipynb"
    if old.exists():
        old.unlink()
        print(f"removed stale  {old.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
