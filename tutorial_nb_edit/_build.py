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
        # Layer 2 — Agentic Reasoning
        ### The RCP Framework, distilled into one runnable notebook

        This notebook is the **interactive showcase** for Layer 2 of the
        RCP Framework — a SQL-backed agentic architecture that takes a
        natural-language query about industrial products, picks a reasoning
        strategy, executes a sequence of functions to gather evidence, and
        only then synthesises an answer once a verifier signs off.

        Everything is here: schema, templates, state machine, workflow nodes,
        function library, prompts, vector index. You read each piece, run it,
        modify it.

        ---

        ### Where this notebook sits in the project

        ```mermaid
        flowchart TB
            subgraph L1[Layer 1 — Extraction]
                P1[PDF catalog]
                S1[VLM-driven extraction pipeline]
                P1 --> S1
            end

            subgraph DB[Storage]
                HDB[(harvested.db<br/>products + families + categories)]
                ADB[(agentic.db<br/>strategies + sessions)]
            end

            subgraph L2[Layer 2 — Agentic Reasoning  ★ this notebook ★]
                Q([User query])
                G[Goal &middot Strategy &middot Function]
                A([Verified answer])
                Q --> G --> A
            end

            subgraph L3[Layer 3 — User Interface]
                W[Flask + SSE web app]
            end

            S1 --> HDB
            G <--> HDB
            G <--> ADB
            W --> G

            style L2 fill:#fff3cd,stroke:#856404,stroke-width:2px
        ```

        L1 builds the product database from PDF catalogs.
        **L2 (this notebook) is the brain** — it answers questions over that database.
        L3 wraps L2 in HTTP for a web UI.

        ---

        ### What you'll build, end-to-end

        ```mermaid
        flowchart LR
            S1[§1 Setup] --> S2[§2 Tour DB]
            S2 --> S3[§3 Schema]
            S3 --> S4[§4 Seed templates]
            S4 --> S5[§5 SessionState]
            S5 --> S6[§6 Function library]
            S6 --> S7[§7 Workflow nodes]
            S7 --> S8[§8 LangGraph]
            S8 --> S9[§9 Run queries]
        ```

        | Built in | What it is |
        |----------|------------|
        | §3 | `agentic.db` from a 9-table SQL schema, alongside this notebook |
        | §4 | Seven strategies + fourteen function templates seeded into `agentic.db` |
        | §6 | Function library + multi-tier LLM helpers + ChromaDB-backed semantic search |
        | §7 | Seven LangGraph nodes with tri-condition routing |
        | §8 | A compiled state machine — same topology as the production project |
        | §9 | End-to-end runs against real queries (live-traced per node) |

        ---

        ### Production-feature parity

        This notebook now mirrors the production codebase feature-for-feature.
        Where the production code has a 1200-line `DatabaseManager`, the
        notebook ships a focused 150-line equivalent with the same API.
        Where the production code splits LLM tiers (`basic` / `reasoning` /
        `multimodal`), the notebook does too. Vector search via ChromaDB
        runs the same `Semantic Search` function the production library
        does. Parallel function execution (`[A || B]` syntax) is wired in.

        | Production file | Notebook section |
        |-----------------|------------------|
        | `db/agentic_schema.sql`              | §3 — inline `SCHEMA_SQL` |
        | `db/schema_manager.py`               | §3 — `init_agentic_db()` |
        | `db/connection.py`                   | §1 — direct `sqlite3.connect`; §7 has connection helpers |
        | `logic/templates.py`                 | §4 — `STRATEGIES_SEED`, `FUNCTIONS_SEED`, etc. |
        | `logic/database_manager.py`          | §7 — focused `DatabaseManager` class |
        | `logic/llm_helpers.py`               | §6 — `get_basic_llm()`, `get_reasoning_llm()`, retry wrapper |
        | `logic/embeddings.py` + `vector_helpers.py` | §6 — ChromaDB index + `Semantic Search` |
        | `logic/function_library.py`          | §6 — handlers in `FUNCTION_MAP` |
        | `logic/workflow_types.py`            | §5 — `SessionState` TypedDict |
        | `logic/workflow_nodes.py`            | §7 — seven node functions |
        | `logic/state_graph.py`               | §8 — `build_graph()` |
        | `config/prompts.yaml`                | §6 — inline `PROMPTS` dict |
        | `config/prompt_loader.py`            | §6 — small `PromptLoader` class |
        | `config/debug_config.py`             | §6 — `DebugConfig` with level dispatcher |
        | `config/session_config.py`           | §5 — `make_session_state()` |
        | `logic/async_helpers.py`             | §7 — `ThreadPoolExecutor` in parallel branch |

        Items kept lighter for readability (call out inline where they appear):
        - We ship 9 / 15 functions in the library. The remaining 6 are
          straightforward variants you can add by following the pattern in §6.
        - YAML prompt files become a single inline `PROMPTS` dict — same
          expressiveness, no file dependency.

        ---

        ### Prerequisites

        - **Working directory**: this notebook expects `db/harvested.db`
          alongside it. The repo ships a copy in
          `tutorial_nb_edit/db/harvested.db` so you don't touch the main
          database; on Colab, upload the entire `tutorial_nb_edit/` folder.
        - **Python**: 3.10+ with these packages:
          ```
          pip install langgraph requests chromadb
          ```
          The Colab/Ollama bootstrap in §1.5 takes care of installing
          Ollama itself.
        - **Models**: the `§1.5` cell pulls `llama3.2:latest` and
          `nomic-embed-text` automatically.
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
        # ---- one-time pip install in Colab (no-op on local if already installed) ----
        import sys
        if "google.colab" in sys.modules:
            import subprocess
            subprocess.run(
                [sys.executable, "-m", "pip", "install", "-q",
                 "langgraph", "requests", "chromadb"],
                check=True,
            )

        # ---- standard library ----
        import json
        import os
        import re
        import sqlite3
        import time
        from concurrent.futures import ThreadPoolExecutor, as_completed
        from pathlib import Path
        from typing import Any, Callable, Dict, List, Optional, Tuple
        from typing_extensions import TypedDict

        # ---- third-party ----
        import requests                                   # talks to Ollama
        from langgraph.graph import END, StateGraph       # the state machine
        # ChromaDB for vector search (§6); imported lazily inside that cell so
        # the rest of the notebook still works if Chroma isn't installed yet.

        # ---- where the databases live ----
        # Both paths are relative to the notebook's working dir. The repo
        # ships a copy of harvested.db inside tutorial_nb_edit/db/ so this
        # notebook is self-contained — you can zip the folder and run it
        # anywhere (Colab, a colleague's laptop, etc.).
        DB_HARVESTED = "db/harvested.db"          # product data (read-only here)
        DB_AGENTIC   = "db/agentic.db"            # workflow state — we create this in §3

        # ---- LLM endpoints ----
        OLLAMA_URL         = "http://localhost:11434"
        OLLAMA_MODEL       = "llama3.2:latest"     # used for goal/strategy/judge/synthesis
        OLLAMA_REASONING   = "llama3.2:latest"     # swap to phi4 / qwen2.5:14b for harder reasoning
        OLLAMA_EMBED_MODEL = "nomic-embed-text"    # used by ChromaDB in §6 (vector search)

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
        IS_COLAB = "google.colab" in sys.modules or "COLAB_RELEASE_TAG" in os.environ
        print(f"environment              : {'Google Colab' if IS_COLAB else 'local'}")

        print(f"{DB_HARVESTED:25s}",
              f"{Path(DB_HARVESTED).stat().st_size // 1024} KB" if Path(DB_HARVESTED).exists() else "MISSING")
        print(f"{DB_AGENTIC:25s}",
              "(will be created in §3)" if not Path(DB_AGENTIC).exists() else
              f"{Path(DB_AGENTIC).stat().st_size // 1024} KB (existing — will be reset in §3)")

        def ollama_status() -> Tuple[bool, List[str]]:
            try:
                r = requests.get(f"{OLLAMA_URL}/api/tags", timeout=3)
                return True, [m["name"] for m in r.json().get("models", [])]
            except Exception:
                return False, []

        ok, tags = ollama_status()
        if ok:
            print(f"ollama                    reachable, {len(tags)} model(s) loaded")
            for need in (OLLAMA_MODEL, OLLAMA_EMBED_MODEL):
                mark = "✅" if need in tags else "⚠️ "
                print(f"  {mark} {need}")
        else:
            print("ollama                    NOT reachable yet.")
            print("  Local:  start Ollama (`ollama serve`) and pull models, OR run §1.5 below.")
            print("  Colab:  run §1.5 below — it auto-installs Ollama and pulls the models.")
    """),

    md("""
        ## §1.5 Bring up Ollama (Colab + first-time-local helper)

        The reasoning workflow needs an Ollama server reachable on
        `http://localhost:11434` with two models pulled:

        - `llama3.2:latest` — chat / reasoning
        - `nomic-embed-text` — embeddings for the vector index in §6

        **Local machine, already running Ollama:** skip this section, the
        probe above already confirmed reachability.

        **Local machine, no Ollama yet:** install it from
        [ollama.com/download](https://ollama.com/download), run
        `ollama serve` in a terminal, then run the cell below — it will
        just pull missing models if any.

        **Google Colab:** run the cell below as-is. It downloads and starts
        Ollama, then pulls the two models. **Allow ~5 minutes the first
        time** — model downloads are several GB. Switch the runtime to a
        T4 GPU (Runtime → Change runtime type) for noticeably faster
        inference.
    """),
    py("""
        # ── Install Ollama if missing ───────────────────────────────────
        # Skip if a server is already responding.
        if not ollama_status()[0]:
            if IS_COLAB or sys.platform.startswith("linux"):
                print("Installing Ollama (one-time, ~5 min on first run)...")
                # Official install script — Linux + WSL only.
                os.system("curl -fsSL https://ollama.com/install.sh | sh")

                print("Starting `ollama serve` in the background...")
                import subprocess
                subprocess.Popen(
                    ["ollama", "serve"],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                # Wait until the server responds.
                for _ in range(30):
                    if ollama_status()[0]:
                        break
                    time.sleep(1)
                else:
                    raise RuntimeError("Ollama failed to come up. Check the install log above.")
                print("Ollama is up.")
            else:
                # Windows / macOS — install must be done manually.
                raise RuntimeError(
                    "Ollama is not reachable on http://localhost:11434.\\n"
                    "Install from https://ollama.com/download and run `ollama serve`, "
                    "then re-run §1 to confirm and continue here."
                )

        # ── Pull required models if not already present ────────────────
        ok, tags = ollama_status()
        for need in (OLLAMA_MODEL, OLLAMA_EMBED_MODEL):
            if need in tags:
                print(f"  ✅ {need} already pulled")
            else:
                print(f"  ⏳ pulling {need} ...")
                # Stream so you can see progress in Colab.
                os.system(f"ollama pull {need}")

        ok, tags = ollama_status()
        print("\\nFinal Ollama status:", "ready" if ok else "FAILED")
        for t in tags:
            print(" •", t)
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

        > **Note:** the bootstrap below uses a direct `sqlite3.executescript(...)`
        > to run the SQL once. The session-scoped `DatabaseManager` class
        > (mirroring the production wrapper) is built later in §7, after the
        > schema exists.
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
             "Extract Requirements, Semantic Search, Extract Attributes, Analyze With LLM"),

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
            ("Extract Product Number", "extract",  "LLM extracts product codes from the user query."),
            ("Extract Requirements",   "extract",  "LLM extracts structured requirements (pressure/temp/material)."),
            ("Query Database",         "search",   "Lookup by product_code joined to family / category."),
            ("Search Products",        "search",   "Keyword search w/ semantic-search fallback."),
            ("Search Families",        "search",   "Keyword search across product_families."),
            ("Semantic Search",        "search",   "ChromaDB-backed cosine similarity over family blurbs."),
            ("Extract Attributes",     "extract",  "Deterministic attribute extraction from prior outputs."),
            ("Compare Items",          "compare",  "LLM-powered side-by-side comparison of two or more product records."),
            ("Filter Items",           "filter",   "Generic filtering engine with comparison conditions."),
            ("Convert Units",          "convert",  "Unit conversion with LLM assistance for context-dependent cases."),
            ("Analyze With LLM",       "analyze",  "Final synthesis — composes the answer from collected evidence."),
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
            "Semantic Search":  [("query", "Input", "string"), ("top_k", "8", "integer")],
            "Extract Attributes": [("items", "", "json"), ("config", "{}", "json")],
            "Compare Items":   [("items", "", "json"), ("fields", "[]", "json")],
            "Filter Items":    [("items", "", "json"), ("conditions", "[]", "json"), ("mode", "AND", "string")],
            "Convert Units":   [
                ("value", "0", "number"), ("from_unit", "", "string"),
                ("to_unit", "", "string"), ("context", "", "string"),
            ],
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
            "Semantic Search":        [("results", "[]", "json"), ("scores", "[]", "json"),
                                       ("count", "0", "integer"), ("items", "[]", "json")],
            "Extract Attributes":     [("extracted_data", "[]", "json")],
            "Compare Items":          [("comparison_table", "{}", "json"),
                                       ("differences", "[]", "json"),
                                       ("similarities", "[]", "json"),
                                       ("items", "[]", "json")],
            "Filter Items":           [("filtered_items", "[]", "json"), ("count", "0", "integer")],
            "Convert Units":          [("converted_value", "0", "number"),
                                       ("from_unit", "", "string"),
                                       ("to_unit", "", "string"),
                                       ("explanation", "", "string")],
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
        ### LLM helpers — multi-tier Ollama with retry and embeddings

        Same shape as the production `Layer_2_Agentic_Reasoning/logic/llm_helpers.py`:

        - `ollama_chat(...)` — one HTTP call to `/api/chat`.
        - `invoke_llm_with_retry(...)` — exponential backoff (1s → 2s → 4s) for transient failures.
        - `get_basic_llm()` / `get_reasoning_llm()` — tier dispatch.
          Different stages of the workflow want different models. `Goal definition`
          and `strategy selection` are happy with a fast 3B model. `Goal validation`
          (the judge) and `Analyze With LLM` (synthesis) benefit from a stronger
          reasoning model. The notebook lets you swap them independently via
          the `OLLAMA_MODEL` / `OLLAMA_REASONING` constants in §1.
        - `get_embedding_model()` + `embed(...)` — produces vectors for
          ChromaDB in §6's vector index.

        ```mermaid
        flowchart LR
            subgraph Tiers
                B[basic LLM<br/>fast / cheap]
                R[reasoning LLM<br/>more careful]
                E[embedding model<br/>nomic-embed-text]
            end
            GD[GoalDefine] --> B
            SP[StrategyPlan] --> B
            EXP[Extract Product Number] --> B
            EXR[Extract Requirements] --> B
            ANA[Analyze With LLM] --> R
            JUD[GoalValidate / judge] --> R
            SS[Semantic Search] --> E
        ```
    """),
    py("""
        # ---- single low-level call --------------------------------------
        def ollama_chat(messages: List[Dict[str, str]], temperature: float = 0.0,
                        model: str = OLLAMA_MODEL) -> str:
            \"\"\"POST /api/chat → return content string.\"\"\"
            r = requests.post(
                f"{OLLAMA_URL}/api/chat",
                json={"model": model, "messages": messages,
                      "stream": False, "options": {"temperature": temperature}},
                timeout=180,
            )
            r.raise_for_status()
            return r.json()["message"]["content"]


        # ---- retry wrapper (mirrors invoke_llm_with_retry from llm_helpers.py) ----
        def invoke_llm_with_retry(messages: List[Dict[str, str]], *,
                                  temperature: float = 0.0,
                                  model: str = OLLAMA_MODEL,
                                  max_retries: int = 3,
                                  base_delay: float = 1.0) -> str:
            \"\"\"Exponential backoff. Re-raise on terminal errors (model not found, etc.).\"\"\"
            last: Optional[Exception] = None
            for attempt in range(max_retries):
                try:
                    return ollama_chat(messages, temperature=temperature, model=model)
                except Exception as e:
                    last = e
                    msg = str(e).lower()
                    if "not found" in msg or "invalid" in msg:
                        raise                              # don't retry terminal errors
                    if attempt < max_retries - 1:
                        delay = base_delay * (2 ** attempt)
                        print(f"  ⏳ LLM attempt {attempt+1} failed: {e}; retrying in {delay:.1f}s")
                        time.sleep(delay)
            raise last  # type: ignore[misc]


        # ---- tier dispatch (matches llm_helpers.get_basic_llm / get_reasoning_llm) ----
        def chat_basic(messages: List[Dict[str, str]], *, temperature: float = 0.0) -> str:
            return invoke_llm_with_retry(messages, temperature=temperature, model=OLLAMA_MODEL)


        def chat_reasoning(messages: List[Dict[str, str]], *, temperature: float = 0.0) -> str:
            return invoke_llm_with_retry(messages, temperature=temperature, model=OLLAMA_REASONING)


        # ---- embeddings (powers the vector store in §6 below) ------------
        def embed(text: str, *, model: str = OLLAMA_EMBED_MODEL) -> List[float]:
            r = requests.post(
                f"{OLLAMA_URL}/api/embeddings",
                json={"model": model, "prompt": text},
                timeout=60,
            )
            r.raise_for_status()
            return r.json()["embedding"]


        def embed_many(texts: List[str], *, model: str = OLLAMA_EMBED_MODEL) -> List[List[float]]:
            return [embed(t, model=model) for t in texts]


        # smoke
        print("chat_basic    :", chat_basic([{"role": "user", "content": "Say only the word: ok"}]).strip())
        v = embed("hydraulic hose for boiling water")
        print(f"embed         : {len(v)}-dim vector, first 4 = {[round(x, 4) for x in v[:4]]}")
    """),
    md("""
        ### Prompts + a small `PromptLoader`

        Production keeps prompts in `prompts.yaml` and loads them through a
        `PromptLoader` class. We inline the prompts as a Python dict — same
        expressiveness, no file dependency — and add a tiny loader class
        that gives us the same `format_prompt(category, **kwargs)` API the
        production workflow nodes call.
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


        # ---- Mini PromptLoader (mirrors config/prompt_loader.py API) ------
        class PromptLoader:
            \"\"\"Same `format_prompt(category, **kwargs)` API as production.\"\"\"
            def __init__(self, prompts: Dict[str, Dict[str, str]]):
                self._p = prompts

            def get(self, category: str) -> Dict[str, str]:
                if category not in self._p:
                    raise KeyError(f"unknown prompt: {category}")
                return self._p[category]

            def format_prompt(self, category: str, **kwargs) -> List[Dict[str, str]]:
                tpl = self.get(category)
                return [
                    {"role": "system", "content": tpl["system"]},
                    {"role": "user",   "content": tpl["user"].format(**kwargs)},
                ]


        prompt_loader = PromptLoader(PROMPTS)
        # `fmt_prompt` (defined above) and `prompt_loader.format_prompt(...)` are
        # interchangeable — keep both so existing callers and the production
        # API surface both work.
    """),

    md("""
        ### `DebugConfig` — verbosity dial

        Production has `config/debug_config.py` with named print categories
        (`print_goal`, `print_strategy`, `print_function`, …) gated by an
        integer level. We compress that into a single dispatcher here so
        you can `debug.set_level(3)` to see everything, `debug.set_level(0)`
        to silence it.
    """),
    py("""
        class DebugConfig:
            LEVELS = {0: "SILENT", 1: "MINIMAL", 2: "NORMAL", 3: "DETAILED", 4: "VERBOSE"}

            def __init__(self, level: int = 1) -> None:
                self.level = level

            def set_level(self, level: int) -> None:
                self.level = level
                print(f"[debug] level = {level} ({self.LEVELS.get(level, '?')})")

            def _emit(self, label: str, msg: str, min_level: int) -> None:
                if self.level >= min_level:
                    print(f"  [{label}] {msg}")

            # categories
            def goal       (self, m): self._emit("Goal",       m, 1)
            def strategy   (self, m): self._emit("Strategy",   m, 1)
            def function   (self, m): self._emit("Function",   m, 2)
            def params     (self, m): self._emit("Params",     m, 3)
            def outputs    (self, m): self._emit("Outputs",    m, 3)
            def validation (self, m): self._emit("Validation", m, 2)
            def warning    (self, m): self._emit("WARN",       m, 1)
            def error      (self, m): self._emit("ERR",        m, 1)
            def system     (self, m): self._emit("System",     m, 0)


        debug = DebugConfig(level=1)        # bump to 3 for params + outputs traces
        debug.system("DebugConfig ready (level=1).")
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
        ### ChromaDB vector index — for `Semantic Search` and `Search Products`

        Plain `LIKE` finds rows that share a literal substring. It misses
        synonyms ("hot water" vs "boiling water"), paraphrases, and
        cross-language matches. ChromaDB gives us cosine similarity over
        Ollama embeddings instead.

        ```mermaid
        flowchart LR
            subgraph Build[Build (one-time)]
                F[(product_families rows)]
                T[Concatenated description<br/>+ applications + name]
                E[nomic-embed-text]
                C[(Chroma collection)]
                F --> T --> E --> C
            end

            subgraph Query[Query]
                Q([user query]) --> EQ[embed query]
                EQ --> S[similarity search<br/>top-k]
                C --> S
                S --> R([ranked families])
            end
        ```

        We index `product_families` rows because that's where the rich text
        lives (`applications` and `description`). `products` rows are mostly
        numeric specs — they're better looked up by code via SQL.
    """),
    py("""
        # ---- Build / open the Chroma collection -------------------------
        # Persistent on disk under db/chroma/, so re-running this cell is fast.
        try:
            import chromadb
        except ImportError:
            raise RuntimeError(
                "chromadb not installed. Run: pip install chromadb\\n"
                "On Colab the §1 setup cell already does this; restart the kernel if needed."
            )

        CHROMA_DIR = "db/chroma"
        chroma_client = chromadb.PersistentClient(path=CHROMA_DIR)

        def build_or_open_family_index(reset: bool = False) -> Any:
            \"\"\"Embed every product_families row once; return the collection.\"\"\"
            name = "product_families"
            existing = {c.name for c in chroma_client.list_collections()}
            if reset and name in existing:
                chroma_client.delete_collection(name)
                existing.discard(name)

            coll = chroma_client.get_or_create_collection(name)
            if coll.count() > 0:
                debug.system(f"Chroma collection '{name}' has {coll.count()} docs (reuse).")
                return coll

            debug.system(f"Building Chroma collection '{name}' …")
            rows = db_query(DB_HARVESTED, '''
                SELECT family_code, name, subtitle, description, applications, page_number
                FROM product_families
            ''')
            ids, docs, metas = [], [], []
            for r in rows:
                blurb = " | ".join(filter(None, [
                    r["name"], r["subtitle"], r["description"], r["applications"],
                ]))
                if not blurb.strip():
                    continue
                ids.append(r["family_code"])
                docs.append(blurb)
                metas.append({"family_code": r["family_code"],
                              "name": r["name"] or "",
                              "page_number": r["page_number"] or 0})

            # Embed in batches so progress is visible.
            BATCH = 32
            for i in range(0, len(docs), BATCH):
                chunk = docs[i:i + BATCH]
                vecs  = [embed(d) for d in chunk]
                coll.add(ids=ids[i:i + BATCH], documents=chunk,
                         embeddings=vecs, metadatas=metas[i:i + BATCH])
                print(f"  embedded {min(i + BATCH, len(docs))}/{len(docs)}", end="\\r")
            print()
            debug.system(f"Chroma index ready: {coll.count()} docs.")
            return coll


        family_collection = build_or_open_family_index(reset=False)
    """),

    md("""
        ### Function: **Semantic Search** (vector-backed)
    """),
    py("""
        def func_semantic_search(params: Dict[str, Any]) -> Tuple[bool, dict]:
            query   = params.get("query") or params.get("Input") or ""
            top_k   = int(params.get("top_k", 8) or 8)
            if not query.strip():
                return False, "no query"

            qvec = embed(query)
            res = family_collection.query(query_embeddings=[qvec], n_results=top_k)

            # Chroma returns parallel lists; flatten into one item per match.
            items: List[dict] = []
            for fid, doc, meta, dist in zip(
                res["ids"][0], res["documents"][0],
                res["metadatas"][0], res["distances"][0],
            ):
                items.append({
                    "family_code": meta["family_code"],
                    "name":        meta["name"],
                    "page_number": meta["page_number"],
                    "snippet":     doc[:200],
                    "score":       round(1.0 - dist, 4),    # cos similarity ≈ 1 − distance
                })

            return True, {"results": items, "scores": [it["score"] for it in items],
                          "count": len(items), "items": items}
    """),

    md("""
        ### Function: **Search Products**

        Keyword + semantic search. We do the SQL filter first (cheap) and
        then re-rank with embeddings if the query needs paraphrase tolerance.
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

            # Fallback to semantic search if SQL came up empty (paraphrase / synonym).
            if not items:
                debug.function("Search Products: SQL LIKE empty → semantic fallback")
                ok, vec_result = func_semantic_search({"query": keywords, "top_k": limit})
                if ok:
                    items = vec_result["items"]

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

            answer = chat_reasoning(                                    # use the heavier tier for synthesis
                fmt_prompt("analyze_with_llm", context=context, question=question),
                temperature=0.1,
            )
            return True, {"Analysis": answer.strip()}
    """),

    md("""
        ### Function: **Compare Items** (LLM-driven)

        Used by the `MULTI-PRODUCT COMPARISON` strategy. Produces a side-by-
        side comparison from a list of items the previous function fetched.
    """),
    py("""
        COMPARE_PROMPT = {
            "system":
                "You compare two or more product records side-by-side.\\n"
                "Return JSON only:\\n"
                "{\\n"
                '  "comparison_table": {"<field>": ["<val for item1>", "<val for item2>", ...]},\\n'
                '  "differences":  ["short bullet", ...],\\n'
                '  "similarities": ["short bullet", ...]\\n'
                "}\\n"
                "Pick fields that genuinely differ where possible.",
            "user":
                "ITEMS:\\n{items_json}\\n\\n"
                "Restrict to these fields if non-empty (otherwise pick interesting ones):\\n"
                "{fields_json}\\n\\n"
                "Return JSON.",
        }
        PROMPTS["compare_items"] = COMPARE_PROMPT


        def func_compare_items(params: Dict[str, Any]) -> Tuple[bool, dict]:
            items = params.get("items") or []
            if isinstance(items, str):
                try: items = json.loads(items)
                except Exception: items = []
            if not isinstance(items, list) or len(items) < 2:
                return False, "need at least 2 items to compare"

            fields = params.get("fields") or []
            if isinstance(fields, str):
                try: fields = json.loads(fields)
                except Exception: fields = []

            out = chat_reasoning(fmt_prompt("compare_items",
                items_json=json.dumps(items[:6], default=str, ensure_ascii=False)[:5000],
                fields_json=json.dumps(fields, ensure_ascii=False),
            ), temperature=0.0)
            data = parse_json_response(out) or {
                "comparison_table": {}, "differences": [], "similarities": [],
            }
            data["items"] = items                                        # pass-through for analyzer
            return True, data
    """),

    md("""
        ### Function: **Filter Items** (deterministic)

        A compact rules engine — accepts a list of items + a list of
        conditions like `[("specs.spec_arb_tr__mpa", ">=", 30)]` and
        returns the matching subset. No LLM.
    """),
    py("""
        def _get_path(d: Any, dotted: str) -> Any:
            \"\"\"Walk 'a.b.c' through dicts; tolerant of None.\"\"\"
            cur = d
            for part in dotted.split("."):
                if isinstance(cur, dict):
                    cur = cur.get(part)
                else:
                    return None
            return cur


        def _cmp(a: Any, op: str, b: Any) -> bool:
            try:
                if op in (">", ">=", "<", "<=", "=", "=="):
                    fa, fb = float(a), float(b)
                    return {">": fa > fb, ">=": fa >= fb, "<": fa < fb,
                            "<=": fa <= fb, "=": fa == fb, "==": fa == fb}[op]
                if op == "!=":
                    return a != b
                if op == "contains":
                    return str(b).lower() in str(a or "").lower()
                if op == "in":
                    return a in (b or [])
            except Exception:
                pass
            return False


        def func_filter_items(params: Dict[str, Any]) -> Tuple[bool, dict]:
            items = params.get("items") or []
            if isinstance(items, str):
                try: items = json.loads(items)
                except Exception: items = []
            conditions = params.get("conditions") or []
            if isinstance(conditions, str):
                try: conditions = json.loads(conditions)
                except Exception: conditions = []
            mode = (params.get("mode") or "AND").upper()

            def keep(it: dict) -> bool:
                results = [_cmp(_get_path(it, c["field"]), c["op"], c["value"])
                           for c in conditions]
                return all(results) if mode == "AND" else any(results)

            kept = [it for it in items if isinstance(it, dict) and keep(it)]
            return True, {"filtered_items": kept, "count": len(kept)}
    """),

    md("""
        ### Function: **Convert Units** (LLM-assisted)

        Standard conversions are mathematical; non-standard ones (like
        `Nm → ft·lb at this torque scale`) need context. We ask the LLM
        to provide a value + brief explanation.
    """),
    py("""
        CONVERT_PROMPT = {
            "system":
                "You are an expert in technical unit conversions.\\n"
                "Reply with JSON only:\\n"
                '{"converted_value": <number>, "explanation": "<one sentence>"}\\n'
                "If the conversion is ambiguous, state the assumption made.",
            "user":
                "Convert {value} {from_unit} to {to_unit}.\\n"
                "Context (if any): {context}\\n"
                "Return JSON.",
        }
        PROMPTS["convert_units"] = CONVERT_PROMPT


        def func_convert_units(params: Dict[str, Any]) -> Tuple[bool, dict]:
            value     = params.get("value")
            from_unit = params.get("from_unit") or ""
            to_unit   = params.get("to_unit") or ""
            ctx       = params.get("context") or ""
            if not from_unit or not to_unit:
                return False, "from_unit / to_unit required"

            out = chat_basic(fmt_prompt("convert_units",
                value=value, from_unit=from_unit, to_unit=to_unit, context=ctx,
            ), temperature=0.0)
            data = parse_json_response(out) or {}
            return True, {
                "converted_value": data.get("converted_value", 0),
                "from_unit":       from_unit,
                "to_unit":         to_unit,
                "explanation":     data.get("explanation", ""),
            }
    """),

    md("""
        ### Registry — `FUNCTION_MAP` is what the workflow dispatches against
    """),
    py("""
        FUNCTION_MAP: Dict[str, Callable[[Dict[str, Any]], Tuple[bool, Any]]] = {
            "Extract Product Number": func_extract_product_number,
            "Extract Requirements":   func_extract_requirements,
            "Query Database":         func_query_database,
            "Search Products":        func_search_products,
            "Search Families":        func_search_families,
            "Semantic Search":        func_semantic_search,
            "Extract Attributes":     func_extract_attributes,
            "Compare Items":          func_compare_items,
            "Filter Items":           func_filter_items,
            "Convert Units":          func_convert_units,
            "Analyze With LLM":       func_analyze_with_llm,
        }
        print(f"Functions registered: {len(FUNCTION_MAP)}")
        for n in FUNCTION_MAP:
            print("  •", n)
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

        Small free functions used by the node implementations below. The
        full session-scoped `DatabaseManager` class is defined right after
        these — workflow nodes use a mix of both depending on how much
        ceremony each call needs.
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
        ### A focused `DatabaseManager` class

        The production project routes every workflow DB call through a
        `DatabaseManager` (1233 lines) which gives session-scoped APIs,
        connection reuse, and transactional helpers. We mirror its
        **public API** (the methods the workflow nodes actually call) in a
        ~150-line class. Anything the production version exposes that the
        notebook doesn't use yet is a method you'd add by following the
        existing patterns.
    """),
    py("""
        class DatabaseManager:
            \"\"\"Session-scoped wrapper around agentic.db. Same method shape as the production class.\"\"\"

            def __init__(self, db_path: str = DB_AGENTIC):
                self.db_path = db_path

            # ---- low-level helpers ---------------------------------------
            def _exec(self, sql: str, params: tuple = ()) -> Optional[int]:
                with sqlite3.connect(self.db_path) as con:
                    cur = con.execute(sql, params)
                    con.commit()
                    return cur.lastrowid

            def _fetch(self, sql: str, params: tuple = ()) -> List[dict]:
                return db_query(self.db_path, sql, params)

            # ---- goals ---------------------------------------------------
            def create_goal(self, session_id: int, description: str,
                            name: str = "MainGoal", target: str = "") -> int:
                return self._exec(
                    "INSERT INTO GoalInSession (SessionID, GoalName, GoalTarget, GoalDescription) "
                    "VALUES (?, ?, ?, ?)",
                    (session_id, name, target, description),
                ) or 0

            def update_goal_status(self, gid: int, success: bool) -> None:
                self._exec("UPDATE GoalInSession SET GoalSuccess = ? WHERE GoalID = ?",
                           (1 if success else 0, gid))

            def get_goal_info(self, gid: int) -> Optional[dict]:
                rows = self._fetch("SELECT * FROM GoalInSession WHERE GoalID = ?", (gid,))
                return rows[0] if rows else None

            # ---- strategies ----------------------------------------------
            def get_available_strategies(self) -> List[str]:
                return [r["StrategyName"] for r in self._fetch(
                    "SELECT StrategyName FROM StrategyLibrary ORDER BY StrategyID")]

            def get_strategy_info(self, name: str) -> Optional[dict]:
                rows = self._fetch(
                    "SELECT * FROM StrategyLibrary WHERE StrategyName = ?", (name,))
                return rows[0] if rows else None

            def get_tried_strategies(self, gid: int) -> List[str]:
                return [r["StrategyName"] for r in self._fetch(
                    "SELECT DISTINCT StrategyName FROM StrategyInSession WHERE GoalID = ?",
                    (gid,))]

            def get_successful_strategies(self, gid: int) -> List[int]:
                return [r["StrategyID"] for r in self._fetch(
                    "SELECT StrategyID FROM StrategyInSession "
                    "WHERE GoalID = ? AND StrategySuccess = 1", (gid,))]

            def create_strategy(self, gid: int, name: str, plan: str) -> int:
                meta = self.get_strategy_info(name) or {}
                return self._exec(
                    "INSERT INTO StrategyInSession "
                    "(GoalID, StrategyName, StrategyTarget, StrategyDescription, PlanSteps) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (gid, name, meta.get("StrategyTarget", ""),
                     meta.get("StrategyDescription", ""), plan),
                ) or 0

            def update_strategy_status(self, sid: int, success: int, validation: str) -> None:
                self._exec(
                    "UPDATE StrategyInSession SET StrategySuccess = ?, StrategyValidation = ? "
                    "WHERE StrategyID = ?",
                    (success, validation, sid),
                )

            def get_strategy_outputs(self, sid: int) -> List[Tuple[str, str]]:
                rows = self._fetch('''
                    SELECT o.OutputName, o.OutputValue
                    FROM FunctionOutputInSession o
                    JOIN FunctionInSession f ON f.FunctionID = o.FunctionID
                    WHERE f.StrategyID = ?
                    ORDER BY o.FunctionOutputID
                ''', (sid,))
                return [(r["OutputName"], r["OutputValue"]) for r in rows]

            def get_strategy_function_statistics(self, sid: int) -> dict:
                row = self._fetch('''
                    SELECT
                      COUNT(*) AS total,
                      SUM(CASE WHEN FunctionSuccess = 1 THEN 1 ELSE 0 END) AS succeeded,
                      SUM(CASE WHEN FunctionSuccess = 0 THEN 1 ELSE 0 END) AS failed,
                      SUM(CASE WHEN FunctionSuccess IS NULL THEN 1 ELSE 0 END) AS pending
                    FROM FunctionInSession WHERE StrategyID = ?
                ''', (sid,))[0]
                return {k: row[k] or 0 for k in ("total", "succeeded", "failed", "pending")}

            # ---- functions -----------------------------------------------
            def create_strategy_functions(self, sid: int, sname: str, plan_steps: str) -> None:
                \"\"\"Insert FunctionInSession rows for every step (incl. parallel groups).\"\"\"
                # Parse `[A || B]` into ('parallel', [A, B]); plain names stay sequential.
                steps: List[Tuple[str, Any]] = []
                for tok in [s.strip() for s in plan_steps.split(",")]:
                    if tok.startswith("[") and tok.endswith("]"):
                        steps.append(("parallel",
                                      [f.strip() for f in tok[1:-1].split("||")]))
                    else:
                        steps.append(("seq", tok))
                # Flatten in execution order: parallel siblings get inserted in batch order.
                for kind, payload in steps:
                    names = payload if kind == "parallel" else [payload]
                    for fname in names:
                        fid = self._exec(
                            "INSERT INTO FunctionInSession "
                            "(StrategyID, StrategyName, FunctionName) VALUES (?, ?, ?)",
                            (sid, sname, fname),
                        ) or 0
                        # Copy parameter templates for this function.
                        for t in self._fetch('''
                            SELECT pl.ParameterName, pl.ParameterValue, pl.Type
                            FROM FunctionParametersLibrary pl
                            JOIN FunctionTemplateLibrary fl ON fl.FunctionTemplateID = pl.FunctionTemplateID
                            WHERE fl.FunctionName = ?
                        ''', (fname,)):
                            self._exec(
                                "INSERT INTO FunctionParametersInSession "
                                "(FunctionID, FunctionName, StrategyName, ParameterName, ParameterValue, Type) "
                                "VALUES (?, ?, ?, ?, ?, ?)",
                                (fid, fname, sname, t["ParameterName"],
                                 t["ParameterValue"], t["Type"]),
                            )

            def get_current_function_id(self, sid: int) -> Optional[int]:
                rows = self._fetch(
                    "SELECT FunctionID FROM FunctionInSession "
                    "WHERE StrategyID = ? AND FunctionSuccess IS NULL "
                    "ORDER BY FunctionID LIMIT 1", (sid,))
                return rows[0]["FunctionID"] if rows else None

            def get_function_info(self, fid: int) -> Optional[dict]:
                rows = self._fetch(
                    "SELECT * FROM FunctionInSession WHERE FunctionID = ?", (fid,))
                return rows[0] if rows else None

            def update_function_status(self, fid: int, success: bool, msg: str = "") -> None:
                self._exec(
                    "UPDATE FunctionInSession SET FunctionSuccess = ?, failedtext = ? "
                    "WHERE FunctionID = ?",
                    (1 if success else 0, msg if not success else "", fid),
                )

            def store_function_output(self, fid: int, fname: str, sname: str,
                                      oname: str, ovalue: str, otype: str) -> None:
                self._exec(
                    "INSERT INTO FunctionOutputInSession "
                    "(FunctionID, FunctionName, StrategyName, OutputName, OutputValue, Type) "
                    "VALUES (?, ?, ?, ?, ?, ?)",
                    (fid, fname, sname, oname, ovalue, otype),
                )


        # Single shared instance — same pattern as the production project.
        db_mgr = DatabaseManager()
        debug.system(f"DatabaseManager bound to {db_mgr.db_path}")
    """),

    md("""
        ### `node_goal_define` — capture the goal
    """),
    py("""
        def node_goal_define(state: SessionState) -> SessionState:
            sess  = state["sessionID"]
            query = state["query"].strip()
            goal_resp = chat_basic(fmt_prompt("goal_definition", query=query))
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
                resp = chat_basic(fmt_prompt(
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

        Six clearly-labelled stages in the cell below:

        1. **Look up** which function we're running (from `FunctionInSession`).
        2. **Detect parallel siblings**: if the current function name is in a
           `[A || B]` group within this strategy's `PlanSteps`, batch all
           pending siblings and run them on a `ThreadPoolExecutor`.
        3. **Resolve parameters**: each row in `FunctionParametersInSession`
           tells us where a value comes from — the user query (`"Input"`),
           a prior function's output (empty string), or a literal template value.
        4. **Dispatch** to the registered handler in `FUNCTION_MAP`.
        5. **Persist** the success flag and any failure text.
        6. **Store outputs** that match the declared output schema; promote
           `Analyze With LLM`'s `Analysis` to the user-visible `finalAnswer`.
    """),
    py("""
        # ─── helpers used by node_function_execute ──────────────────────

        def parse_plan_groups(plan_steps: str) -> List[List[str]]:
            \"\"\"Return the parallel groups in this strategy's PlanSteps.\"\"\"
            groups: List[List[str]] = []
            for tok in [s.strip() for s in plan_steps.split(",")]:
                if tok.startswith("[") and tok.endswith("]"):
                    groups.append([f.strip() for f in tok[1:-1].split("||")])
            return groups


        def find_parallel_siblings(sid: int, fn: str) -> Optional[List[int]]:
            \"\"\"If `fn` is in a parallel group for strategy `sid`, return the FIDs of all pending siblings.\"\"\"
            row = db_query(DB_AGENTIC,
                "SELECT PlanSteps FROM StrategyInSession WHERE StrategyID = ?", (sid,))
            if not row:
                return None
            groups = parse_plan_groups(row[0]["PlanSteps"])
            for g in groups:
                if fn in g:
                    pending = db_query(DB_AGENTIC, '''
                        SELECT FunctionID, FunctionName FROM FunctionInSession
                        WHERE StrategyID = ? AND FunctionSuccess IS NULL
                          AND FunctionName IN (%s)
                        ORDER BY FunctionID
                    ''' % ",".join("?" * len(g)), (sid, *g))
                    return [r["FunctionID"] for r in pending]
            return None


        def _resolve_params(fid: int, sid: int, fn: str, query: str) -> Dict[str, Any]:
            \"\"\"Read FunctionParametersInSession and fill in actual values.\"\"\"
            param_rows = db_query(DB_AGENTIC,
                "SELECT ParameterName, ParameterValue, Type FROM FunctionParametersInSession "
                "WHERE FunctionID = ?", (fid,))
            out: Dict[str, Any] = {}
            for p in param_rows:
                name, val, ptype = p["ParameterName"], p["ParameterValue"], p["Type"]
                if val == "Input":
                    out[name] = query
                elif val == "":
                    merged = collect_outputs(sid, name)
                    if not merged and name == "Input":
                        merged = [query]
                    out[name] = merge_values(name, merged) if merged else ""
                else:
                    if ptype == "json":
                        try:    out[name] = json.loads(val)
                        except: out[name] = val
                    elif ptype == "integer":
                        try:    out[name] = int(val)
                        except: out[name] = val
                    else:
                        out[name] = val
            return out


        def _persist_function_result(fid: int, fn: str, sname: str,
                                     success: bool, result: Any) -> None:
            \"\"\"Update status + store declared outputs.\"\"\"
            db_exec("UPDATE FunctionInSession SET FunctionSuccess = ?, failedtext = ? "
                    "WHERE FunctionID = ?",
                    (1 if success else 0,
                     "" if success else str(result)[:500], fid))
            if success and isinstance(result, dict):
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


        def _execute_one(fid: int, query: str) -> Tuple[int, str, bool, Any]:
            \"\"\"Worker for both sequential and parallel branches.\"\"\"
            row = db_query(DB_AGENTIC,
                "SELECT FunctionName, StrategyID, StrategyName "
                "FROM FunctionInSession WHERE FunctionID = ?", (fid,))[0]
            fn, sid, sname = row["FunctionName"], row["StrategyID"], row["StrategyName"]
            params = _resolve_params(fid, sid, fn, query)
            handler = FUNCTION_MAP.get(fn)
            if not handler:
                return fid, fn, False, f"no handler for {fn!r}"
            try:
                ok, res = handler(params)
            except Exception as e:
                ok, res = False, f"{type(e).__name__}: {e}"
            return fid, fn, ok, res


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

            # ─── 2. Parallel siblings? Batch them. ──────────────────────
            siblings = find_parallel_siblings(sid, fn)
            if siblings and len(siblings) > 1:
                trace("FunctionExecute", f"parallel batch: {siblings}")
                with ThreadPoolExecutor(max_workers=min(4, len(siblings))) as ex:
                    futures = [ex.submit(_execute_one, sfid, query) for sfid in siblings]
                    any_failed = False
                    for fut in as_completed(futures):
                        sfid, sfn, ok, res = fut.result()
                        _persist_function_result(sfid, sfn, sname, ok, res)
                        trace("FunctionExecute", f"  ↳ {sfn}: {'ok' if ok else 'FAIL'}")
                        if ok and sfn == "Analyze With LLM" and isinstance(res, dict):
                            state["finalAnswer"] = res.get("Analysis", state.get("finalAnswer"))
                        if not ok:
                            any_failed = True
                if any_failed:
                    state["strategyAborted"] = True
                return state

            # ─── 3-6. Sequential single-function path ───────────────────
            # Re-uses the same helpers the parallel branch above used.
            trace("FunctionExecute", f"{fn}")
            _, _, success, result = _execute_one(fid, query)
            _persist_function_result(fid, fn, sname, success, result)

            if success and fn == "Analyze With LLM" and isinstance(result, dict):
                state["finalAnswer"] = result.get("Analysis", state.get("finalAnswer"))
            elif not success:
                state["strategyAborted"] = True
                trace("FunctionExecute", f"{fn} failed → strategy aborted ({result})")

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

            judge_resp = chat_reasoning(fmt_prompt(            # heavier tier for validation
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

        Same topology as the production project. **Tri-condition routing**
        on `StrategyValidate` is the load-bearing decision:

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

        > **Parallel execution** (the `[Func1 || Func2]` syntax in
        > `PlanSteps`) is wired in via `DatabaseManager.create_strategy_functions`
        > (parses the syntax) and the parallel branch in `node_function_execute`
        > (uses `ThreadPoolExecutor`). See the `PARALLEL ENHANCED LOOKUP`
        > strategy seeded in §4 for an example.
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
