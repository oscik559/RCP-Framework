"""
Build Layer 2 (Agentic Reasoning) tutorial notebook.

Run:

    python RCP_notebook/_build_agentic_reasoning.py
"""
from __future__ import annotations
from pathlib import Path

from _nb_helpers import md, py, write_nb

HERE = Path(__file__).resolve().parent


L2_CELLS: list[dict] = [
    md("""
        # Layer 2 — Agentic Reasoning
        ### The RCP Framework, distilled into one runnable notebook

        > 🔗 [github.com/oscik559/RCP-Framework](https://github.com/oscik559/RCP-Framework) — full source, additional cases, eval suites.

        A SQL-backed agentic architecture: takes a natural-language query, picks
        a reasoning **strategy**, runs a sequence of **functions** to gather
        evidence, and synthesises an answer only after a verifier signs off.

        **Target**: technical documentation that fits a *Categories → Families
        → Items* shape (manuals, parts catalogs, SOPs, regulatory texts). We
        use a **product catalog as the sample documentation** here — concrete
        and easy to query — but the framework is generic. Layer 1 produced
        `harvested.db`; this notebook is the brain that queries it.

        > **Run the next cell first** — every diagram below calls `show_mermaid(...)` (mermaid.ink renders the SVG inline; works in Jupyter, VS Code, and Colab).
    """),
    py("""
        def show_mermaid(graph: str) -> None:
            \"\"\"Render a Mermaid diagram inline as an SVG (Colab-compatible).

            We render via mermaid.ink rather than a notebook extension so
            diagrams display the same way on local Jupyter, VS Code, and Colab.
            \"\"\"
            import base64
            from IPython.display import display, HTML
            encoded = base64.urlsafe_b64encode(graph.strip().encode("utf-8")).decode("ascii")
            display(HTML(
                f'<img src="https://mermaid.ink/svg/{encoded}" '
                f'alt="diagram" style="max-width:100%;border:1px solid #eee" />'
            ))
    """),

    py('''
        show_mermaid(r"""
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
        """)
    '''),
    md("""
        L1 builds the database from PDFs. **L2 (this notebook) is the brain.**
        L3 wraps L2 in HTTP for a web UI.

        ---

        ### Source-repo crosswalk

        | Source file | Notebook section |
        |-------------|------------------|
        | [`db/agentic_schema.sql`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/db/agentic_schema.sql) | §3 — inline `SCHEMA_SQL` |
        | [`db/schema_manager.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/db/schema_manager.py) | §3 — `init_agentic_db()` |
        | [`logic/templates.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/logic/templates.py) | §4 — `STRATEGIES_SEED` / `FUNCTIONS_SEED` |
        | [`logic/database_manager.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/logic/database_manager.py) | §7 — free-function helpers |
        | [`logic/llm_helpers.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/logic/llm_helpers.py) | §6 — `chat_basic` / `chat_reasoning` / retry |
        | [`logic/embeddings.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/logic/embeddings.py) + [`vector_helpers.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/logic/vector_helpers.py) | §6 — Chroma index + `Semantic Search` |
        | [`logic/function_library.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/logic/function_library.py) | §6 — `FUNCTION_MAP` handlers |
        | [`logic/workflow_types.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/logic/workflow_types.py) | §5 — `SessionState` |
        | [`logic/workflow_nodes.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/logic/workflow_nodes.py) | §7 — node functions |
        | [`logic/state_graph.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/logic/state_graph.py) | §8 — `build_graph()` |
        | [`config/prompts.yaml`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/config/prompts.yaml) | §6 — inline `PROMPTS` dict |
        | [`config/debug_config.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/config/debug_config.py) | §6 — `DebugConfig` |
        | [`config/session_config.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/config/session_config.py) | §5 — `make_session_state()` |

        ### Prerequisites

        <div class="alert alert-warning"><b>Action Required:</b> Ensure these dependencies are met.</div>

        - `db/harvested.db` next to the notebook (shipped in `RCP_notebook/db/`).
        - Python 3.10+ with `pip install langgraph requests chromadb`. §1.5
          handles Ollama itself and pulls `llama3.2:latest` + `nomic-embed-text:latest`.
        - On Colab, upload the entire `RCP_notebook/` folder.
    """),

    md("""
        ### Notebook map and inventory

        | § | Title | What you do |
        |---|-------|-------------|
        | [§1](#1-Setup-—-imports-paths-databases) | Setup | Paths, imports, environment probe |
        | [§1.5](#15-Bring-up-Ollama-(Google-Colab-or-clean-start)) | Bring up Ollama | Install / start / pull models (skippable if already running) |
        | [§2](#2-Quick-tour-of-harvesteddb) | Tour `harvested.db` | Sanity-check the product data |
        | [§3](#3-Build-agenticdb-—-Agentic-Reasoning-Layer) | Build `agentic.db` | Create the 9-table workflow schema |
        | [§4](#4-Seed-templates) | Seed templates | Strategies, function templates, params, outputs |
        | [§5](#5-Session-state-—-the-dict-that-flows-through-the-graph) | Session state | The dict that flows through the graph |
        | [§6](#6-Function-library-—-10-utilities-+-prompts) | Function library | Ten executable functions + LLM helpers + prompts |
        | [§7](#7-Workflow-nodes) | Workflow nodes | Seven node functions + small DB helpers |
        | [§8](#8-Build-LangGraph) | Build LangGraph | Compile the state machine |
        | [§9](#9-Run-a-query-end-to-end-—-with-live-tracing) | Run queries | End-to-end runs, traced per node |

        > §3/§4/§7 just *define*; fast. §6 first-run embeds ~168 family rows
        > into Chroma via Ollama — a few minutes; subsequent runs reuse the
        > on-disk index. §9 invokes the LLM — seconds per stage.

        Counts referenced throughout the notebook:

        | Kind | Count | Names |
        |------|-------|-------|
        | Strategies (§4) | **6** | DIRECT SPECIFICATION LOOKUP, CONTEXTUAL PRODUCT SEARCH, STANDARD & COMPLIANCE LOOKUP, KNOWLEDGE BASE & RAG, MULTI-PRODUCT COMPARISON, FAMILY DEEP-DIVE |
        | `FUNCTION_MAP` entries (§6) | **10** | Extract Product Number, Extract Requirements, Query Database, Search Products, Search Families, Semantic Search, Extract Attributes, Compare Items, Filter Items, Analyze With LLM |
        | Used by seeded strategies | **8** | (above minus `Search Products` and `Filter Items` — defined-but-unscheduled; wire them in as the §4 extension exercise) |
        | Workflow nodes (§7) | **7** | GoalDefine, StrategyPlan, FunctionExecute, FunctionValidate, StrategyValidate, GoalValidate, done |
        | Tables in `agentic.db` (§3) | **9** | 5 `*InSession` (trace) + 4 `*Library` (templates) |
    """),

    md("""
        ### Colab only — mount Google Drive (skip on local)

        If you've put `RCP_notebook/` in your Google Drive, run the next cell
        to mount Drive and `cd` into the folder so the relative paths in §1
        resolve. On a local Jupyter / VS Code session this is a no-op — skip it.
    """),
    py("""
        # Mount Google Drive and cd into the notebook folder when on Colab.
        # On local kernels this prints a one-line note and does nothing else.
        import os
        import sys

        if "google.colab" in sys.modules:
            from google.colab import drive
            drive.mount("/content/drive")

            # Edit this if you put `RCP_notebook/` somewhere other than the
            # Drive root (e.g. inside a subfolder).
            DRIVE_PATH = "/content/drive/MyDrive/RCP_notebook"

            if os.path.isdir(DRIVE_PATH):
                os.chdir(DRIVE_PATH)
                print(f"cwd → {DRIVE_PATH}")
            else:
                print(f"⚠️  Not found: {DRIVE_PATH}")
                print("   Edit DRIVE_PATH above, or upload RCP_notebook/ to the Drive root.")
        else:
            print("Not on Colab — Drive mount skipped.")
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
        # ships a copy of harvested.db inside RCP_notebook/db/ so this
        # notebook is self-contained — you can zip the folder and run it
        # anywhere (Colab, a colleague's laptop, etc.).
        DB_HARVESTED = "db/harvested.db"          # product data (read-only here)
        DB_AGENTIC   = "db/agentic.db"            # workflow state — we create this in §3

        # ---- LLM endpoints ----
        OLLAMA_URL         = "http://localhost:11434"
        OLLAMA_MODEL       = "llama3.2:latest"     # used for goal/strategy/judge/synthesis
        OLLAMA_REASONING   = "llama3.2:latest"     # swap to phi4 / qwen2.5:14b for harder reasoning
        OLLAMA_EMBED_MODEL = "nomic-embed-text:latest"    # used by ChromaDB in §6 (vector search)

        # ---- UTF-8 for Swedish text on Windows ----
        if sys.platform.startswith("win"):
            try:
                sys.stdout.reconfigure(encoding="utf-8", errors="replace")
                sys.stderr.reconfigure(encoding="utf-8", errors="replace")
            except Exception:
                pass

        IS_COLAB = "google.colab" in sys.modules or "COLAB_RELEASE_TAG" in os.environ

        print("python                   :", sys.version.split()[0])
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
        ## §1.5 Bring up Ollama (Google Colab or clean start)

        <div class="alert alert-info"><b>Tip:</b> Make sure Ollama is running before proceeding past this section.</div>

        Need an Ollama server on `http://localhost:11434` with `llama3.2:latest`
        (chat/reasoning) and `nomic-embed-text:latest` (embeddings for §6) pulled.

        ### Which cells to run?

        | Situation (per §1 probe) | Action |
        |--------------------------|--------|
        | Reachable, both models ✅ | Skip §1.5; jump to §2. |
        | Reachable, models missing ⚠️ | Run only §1.5c (pull). |
        | Local Linux, no Ollama | §1.5a → §1.5b → §1.5c. |
        | Local macOS / Windows, no Ollama | Install from [ollama.com/download](https://ollama.com/download), start it, re-run §1, then §1.5c. (§1.5a's shell installer is Linux-only.) |
        | Google Colab | Switch to T4 GPU (Runtime → Change runtime type) first, then §1.5a → §1.5b → §1.5c. ~5 min, several GB. |

        Cells are split so a failure tells you which step broke and what its
        output was. The three known gotchas (Colab missing `zstd`, `systemctl`
        on a non-systemd image, background `serve` dying quietly) are handled
        inline — see the comments in each cell below.
    """),
    md("""
        ### §1.5a — Install the binary
    """),
    py("""
        import shutil
        import subprocess

        OLLAMA_BIN = shutil.which("ollama")
        if OLLAMA_BIN:
            print(f"  ✅ ollama binary already present at {OLLAMA_BIN}")
        elif IS_COLAB or sys.platform.startswith("linux"):
            # ── Pre-req: zstd ─────────────────────────────────────────────
            # Recent Ollama installers ship the binary inside a `.tar.zst`
            # archive. The install script extracts it with `tar --zstd`,
            # which needs the `zstd` userland tool. Standard Colab images
            # don't include `zstd` — without it the script silently fails
            # to write `/usr/local/bin/ollama` and the next cell errors out.
            if shutil.which("zstd") is None:
                print("Installing `zstd` (required by the Ollama installer)...")
                subprocess.run(["sudo", "apt-get", "update", "-qq"], check=False)
                subprocess.run(["sudo", "apt-get", "install", "-y", "-qq", "zstd"],
                               check=True)
                print("  ✅ zstd installed")
            else:
                print("  ✅ zstd already present")

            print("Running official Ollama install script (this may take 1–3 min)...")
            # We DO NOT raise on non-zero return: systemctl errors are expected on Colab
            # and don't prevent the binary from being installed.
            ret = subprocess.run(
                "curl -fsSL https://ollama.com/install.sh | sh",
                shell=True,
            ).returncode
            print(f"  install script exit code: {ret} (non-zero is OK on Colab — systemd unavailable)")

            OLLAMA_BIN = shutil.which("ollama")
            if not OLLAMA_BIN:
                # Fallback: the script also drops the binary at /usr/local/bin/ollama
                fallback = "/usr/local/bin/ollama"
                if Path(fallback).exists():
                    OLLAMA_BIN = fallback
                    print(f"  ✅ found binary at {fallback} (not on PATH yet)")
                else:
                    raise RuntimeError(
                        "Ollama install failed: no `ollama` binary found.\\n"
                        "Try running this in a separate cell with !-magic to see full output:\\n"
                        "    !curl -fsSL https://ollama.com/install.sh | sh"
                    )
            else:
                print(f"  ✅ ollama installed at {OLLAMA_BIN}")
        else:
            raise RuntimeError(
                "macOS / Windows: install Ollama from https://ollama.com/download, "
                "then start it (`ollama serve`) and re-run §1."
            )

        # Verify the binary actually runs.
        ver = subprocess.run([OLLAMA_BIN, "--version"], capture_output=True, text=True)
        print("  version:", ver.stdout.strip() or ver.stderr.strip())
    """),
    md("""
        ### §1.5b — Start `ollama serve` in the background

        Keep the `Popen` handle (`ollama_proc`) so the teardown cell at the
        end can `.terminate()` it; stderr goes to `db/ollama_serve.log` so
        we can tail it if startup fails.
    """),
    py("""
        import subprocess

        ollama_proc: Optional[subprocess.Popen] = None

        if ollama_status()[0]:
            print("  ✅ ollama already responding on", OLLAMA_URL)
        else:
            # Stream stderr to a log file we can tail if startup fails.
            log_path = Path("db/ollama_serve.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)
            log_fp = open(log_path, "wb")

            print("Starting `ollama serve` …")
            ollama_proc = subprocess.Popen(
                [OLLAMA_BIN, "serve"],
                stdout=log_fp,
                stderr=subprocess.STDOUT,
            )

            # Poll for readiness up to 60s. Bail out early if the process dies.
            ready = False
            for i in range(60):
                if ollama_proc.poll() is not None:
                    log_fp.close()
                    tail = log_path.read_text(errors="replace")[-2000:]
                    raise RuntimeError(
                        f"ollama serve exited with code {ollama_proc.returncode}.\\n"
                        f"Tail of {log_path}:\\n{tail}"
                    )
                if ollama_status()[0]:
                    ready = True
                    print(f"  ✅ ollama up after {i + 1}s")
                    break
                time.sleep(1)

            if not ready:
                tail = log_path.read_text(errors="replace")[-2000:]
                raise RuntimeError(
                    f"Ollama did not respond within 60s. Tail of {log_path}:\\n{tail}"
                )
    """),
    md("""
        ### §1.5c — Pull the required models

        First pulls download a few GB; subsequent runs are no-ops.
    """),
    py("""
        import subprocess

        for need in (OLLAMA_MODEL, OLLAMA_EMBED_MODEL):
            _, tags = ollama_status()
            if need in tags:
                print(f"  ✅ {need} already pulled")
                continue
            print(f"  ⏳ pulling {need} …  (first time: several minutes)")
            # capture_output=False so download progress streams to the cell.
            ret = subprocess.run([OLLAMA_BIN, "pull", need]).returncode
            if ret != 0:
                raise RuntimeError(f"`ollama pull {need}` failed with exit code {ret}.")
            print(f"  ✅ {need} pulled")

        ok, tags = ollama_status()
        print("\\nFinal Ollama status:", "ready ✅" if ok else "FAILED ❌")
        for t in sorted(tags):
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
        <div class="alert alert-success"><b>Checkpoint:</b> You should see non-zero row counts for categories, product_families, and products above. If not, `harvested.db` is missing or empty.</div>

        ## §3. Build `agentic.db` from scratch

        The framework keeps two databases:
        - `harvested.db` — **product** data (read-only here).
        - `agentic.db` — **workflow** state. Stores every goal, strategy, function call, parameter, and output, plus the **template libraries** the planner reads from.

        The schema has a Goal → Strategy → Function hierarchy mirrored across
        two halves: `*InSession` tables (per-run execution traces) and `*Library`
        tables (reusable templates).

        *(diagram below — rendered by `show_mermaid`)*
    """),
    py('''
        show_mermaid(r"""
        erDiagram
            GoalInSession                ||--o{ StrategyInSession           : "has many"
            StrategyInSession            ||--o{ FunctionInSession           : "has many"
            FunctionInSession            ||--o{ FunctionOutputInSession     : "produces"
            FunctionInSession            ||--o{ FunctionParametersInSession : "consumes"
        
            StrategyLibrary              }o..o| StrategyInSession           : "template for"
            FunctionTemplateLibrary      }o..o| FunctionInSession           : "template for"
            FunctionTemplateLibrary      ||--o{ FunctionParametersLibrary   : "declares"
            FunctionTemplateLibrary      ||--o{ FunctionOutputLibrary       : "declares"
        """)
    '''),
    md("""
        
        Two halves, same shape:
        - **`*Library`** rows are the *catalog* — what strategies and functions exist.
        - **`*InSession`** rows are the *log* — what actually ran for each query, with what params, what outputs, and what success status.

        The SQL below is lifted verbatim from `Layer_2_Agentic_Reasoning/db/agentic_schema.sql`.

        > **Note:** the bootstrap below uses a direct `sqlite3.executescript(...)`
        > to run the SQL once. The session-scoped `DatabaseManager` class
        > (mirroring the wrapper in the repo) is built later in §7, after the
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
                    # FK_OFF lets us drop tables in any order — otherwise SQLite
                    # would refuse on referenced parents. We re-enable below.
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
        ### Inspect — what's inside `agentic.db` right now

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
                marker = "*" if cnt else " "
                print(f"  {marker} {tname:32s} {cnt:>4} rows  ({col_str})")


        inspect_db(DB_AGENTIC)
    """),

    md("""
        ## §4. Seed the template libraries

        The planner picks strategies and functions by **reading from `agentic.db`**,
        not from hardcoded Python. So before we can run anything, the library
        tables need rows.

        The data below is lifted from
        `Layer_2_Agentic_Reasoning/logic/templates.py` — six strategies and
        ten function templates. Each strategy's `PlanSteps` is a comma-
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
             "Extract Product Number, Query Database, Compare Items, Extract Attributes, Analyze With LLM"),

            ("FAMILY DEEP-DIVE",
             "family",
             "Look up everything about a product family (e.g. KAPPAFLEX, 4201).",
             "Search Families, Extract Attributes, Analyze With LLM"),
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
            "Analyze With LLM": [
                ("question", "Input", "string"),
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

        *(diagram below — rendered by `show_mermaid`)*
    """),
    py('''
        show_mermaid(r"""
        flowchart LR
            Q([User query]) --> EPN[Extract Product Number]
            EPN -->|Keyword Output| QDB[Query Database]
            QDB -->|items| EA[Extract Attributes]
            EA -->|extracted_data| ANA[Analyze With LLM]
            ANA --> A([Final answer])
        """)
    '''),
    md("""
        
        Each arrow is data flowing through `FunctionOutputInSession` — one
        function's output becomes the next function's input slot. Slot
        names are declared in `OUTPUTS_SEED` / `PARAMS_SEED` (§4 above).
    """),
    md("""
        ### Try it — peek at any strategy's plan
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
        ## §5. The session state

        Every node reads and writes a single `SessionState` dict. The `TypedDict`
        below documents the shape; the routing logic in §8 keys off the
        `*Satisfied` flags + `judgeConfidence`.

        > `forcedStrategy` (debug knob): if set, `node_strategy_plan` skips
        > LLM-based strategy selection and uses this one instead. Useful for
        > iterating on a single strategy in isolation (see §9.1).
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
        # Descriptions are noun-phrase short labels, all in the same register.
        STATE_FIELDS: List[Tuple[str, str]] = [
            ("query",              "user question (input)"),
            ("sessionID",          "unique per run, scopes session tables"),
            ("currentGoalID",      "→ GoalInSession row"),
            ("currentStrategyID",  "→ StrategyInSession row"),
            ("currentFunctionID",  "→ FunctionInSession row"),
            ("strategySatisfied",  "current strategy finished (success or abort)"),
            ("goalSatisfied",      "judge approved an answer"),
            ("strategyAborted",    "current strategy failed → re-plan"),
            ("workflowComplete",   "all strategies tried OR success"),
            ("judgeConfidence",    "confidence score in [0.0, 1.0]"),
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
        ## §6. The function library

        Ten callable functions plus the LLM/embedding helpers they use. Each
        handler follows the repo's interface:

        ```
        handler(params: dict) -> (success: bool, result: dict | str)
        ```

        Param values come from `FunctionParametersInSession`: `"Input"` resolves
        to the user query, `""` merges from a prior function's output (matched
        by slot name in `FunctionOutputInSession`), anything else is a literal
        from §4. On success, `result` keys must be the **declared outputs** in
        `OUTPUTS_SEED` (§4) — the executor persists those into the trace.
    """),
    md("""
        ### LLM helpers — multi-tier Ollama with retry and embeddings

        - `ollama_chat` — one POST to `/api/chat`.
        - `invoke_llm_with_retry` — 1s → 2s → 4s backoff for transient
          errors; re-raises immediately on terminal errors (model not found),
          so misconfiguration fails fast.
        - `chat_basic` / `chat_reasoning` — tier dispatch. Cheap tier for
          goal/strategy/extract; heavier tier for the judge and final
          synthesis. Swap via `OLLAMA_MODEL` / `OLLAMA_REASONING` in §1.
        - `embed` — vector for ChromaDB.
    """),
    py('''
        show_mermaid(r"""
        flowchart LR
            subgraph Tiers
                B[basic LLM<br/>fast / cheap]
                R[reasoning LLM<br/>more careful]
                E[embedding model<br/>nomic-embed-text:latest]
            end
            GD[GoalDefine] --> B
            SP[StrategyPlan] --> B
            EXP[Extract Product Number] --> B
            EXR[Extract Requirements] --> B
            ANA[Analyze With LLM] --> R
            JUD[GoalValidate / judge] --> R
            SS[Semantic Search] --> E
        """)
    '''),
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
        ### Prompts

        The repo keeps prompts in `prompts.yaml` and loads them through a
        `PromptLoader` class. Inlining them as a Python dict here keeps the
        walk-through self-contained — the same `format_prompt(...)` call shape
        that the workflow nodes in the repo use is exposed below as the
        function `fmt_prompt(...)`.
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

            "compare_items": {
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
        ### `DebugConfig` — verbosity dial

        The repo has [`config/debug_config.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_2_Agentic_Reasoning/config/debug_config.py) with named print categories
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
        `Keyword Output` (the canonical name from the source repo) so
        downstream functions like `Query Database` can pick it up.
    """),
    py("""
        def func_extract_product_number(params: Dict[str, Any]) -> Tuple[bool, dict]:
            # Slot "Input" carries the user query (set by the planner at runtime).
            query = params.get("Input", "") or ""

            # Single LLM call — see PROMPTS['product_code_extraction'] for the prompt.
            out = ollama_chat(fmt_prompt("product_code_extraction", query=query))

            # The prompt asks for comma-separated codes, but small models often
            # newline-separate them. Normalise newlines→commas, strip a leading
            # "Product codes:" label, then keep just the codes.
            text = out.strip()
            text = re.sub(r"^[Pp]roduct codes?:\\s*", "", text)
            text = text.replace("\\n", ", ").replace(";", ", ")
            codes = ", ".join(p.strip().strip('"').strip("'")
                              for p in text.split(",") if p.strip())

            # Output slot name MUST match what's declared in OUTPUTS_SEED for this function.
            return True, {"Keyword Output": codes}
    """),
    md("""
        ### Try it — one function in isolation

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

        `LIKE` misses synonyms ("hot water" vs "boiling water"), paraphrases,
        and cross-language matches. Chroma gives us cosine similarity over
        Ollama embeddings.

        > **Stale-after-Layer-1**: this cell reuses the on-disk index if it
        > has rows. After regenerating `harvested.db`, call
        > `build_or_open_family_index(reset=True)` once.
    """),
    py('''
        show_mermaid(r"""
        flowchart LR
            subgraph Build["Build (one-time)"]
                F[(product_families rows)]
                T["Concatenated description<br/>+ applications + name"]
                E[nomic-embed-text:latest]
                C[(Chroma collection)]
                F --> T --> E --> C
            end
        
            subgraph Query[Query]
                Q([user query]) --> EQ[embed query]
                EQ --> S["similarity search<br/>top-k"]
                C --> S
                S --> R([ranked families])
            end
        """)
    '''),
    md("""
        
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
            # Chroma requires unique ids. The shipped harvested.db has a few
            # duplicate family_codes (4 of 168 rows) — we de-duplicate by
            # family_code, keeping the first non-empty blurb we see, and skip
            # rows where family_code is missing.
            ids, docs, metas = [], [], []
            seen: set[str] = set()
            skipped_dupes = 0
            skipped_blank = 0
            for r in rows:
                code = (r.get("family_code") or "").strip()
                if not code:
                    skipped_blank += 1
                    continue
                if code in seen:
                    skipped_dupes += 1
                    continue
                blurb = " | ".join(filter(None, [
                    r["name"], r["subtitle"], r["description"], r["applications"],
                ]))
                if not blurb.strip():
                    skipped_blank += 1
                    continue
                seen.add(code)
                ids.append(code)
                docs.append(blurb)
                metas.append({"family_code": code,
                              "name": r["name"] or "",
                              "page_number": r["page_number"] or 0})

            if skipped_dupes or skipped_blank:
                debug.system(f"  skipped {skipped_dupes} duplicate, {skipped_blank} blank/empty rows")

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
            # Slot "query" preferred; fall back to "Input" so this also works when
            # called directly with a raw user query (handy for unit tests).
            query   = params.get("query") or params.get("Input") or ""
            top_k   = int(params.get("top_k", 8) or 8)
            if not query.strip():
                return False, "no query"

            qvec = embed(query)
            res = family_collection.query(query_embeddings=[qvec], n_results=top_k)

            # Chroma returns parallel lists (ids[0] is the first query's hits, etc.).
            # Flatten into one item per match. score = 1 - cosine distance ≈ similarity
            # in [0,1] where 1 is identical, so it's friendlier to display than `dist`.
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
                    "score":       round(1.0 - dist, 4),
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

            # Try exact family_code first. Catalog codes are like '1071-00-16'
            # (4-2-2); we accept up to three -N suffixes.
            code_match = re.search(r"\\b(\\d{4}(?:-\\d+){0,3})\\b", keywords)
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

        Flattens upstream `items` into rows of `{product_code, family_code,
        specs: [{label, value, raw_field}, …]}` for the synthesis step.
        Capped at `MAX_ATTRIBUTE_ITEMS` (default 10) — bump it if a search
        returns more hits and you want them all to reach the LLM.
    """),
    py("""
        # Field-label aliases (truncated subset of the glossary in the repo).
        FIELD_LABELS = {
            "spec_arb_tr__mpa": "Working pressure (MPa)",
            "spec_arb_tr__bar": "Working pressure (bar)",
            "spec_id_mm":       "Inner diameter (mm)",
            "spec_yd_mm":       "Outer diameter (mm)",
            "spec_temperatur":  "Temperature range",
            "spec_vikt_kg_m":   "Weight (kg/m)",
            "spec_b_jningsradie_mm": "Min bend radius (mm)",
        }

        MAX_ATTRIBUTE_ITEMS = 10                        # see the markdown note above


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
            for it in items[:MAX_ATTRIBUTE_ITEMS]:              # cap to keep prompts small
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

        Terminal function for every strategy: feeds the collected evidence
        to the LLM with the answer-formatting prompt. Its `Analysis` output
        becomes `state.finalAnswer`. Context truncated to
        `MAX_ANALYSIS_CONTEXT_CHARS` chars (default 6000); raise it if you
        need bigger prompts.
    """),
    py("""
        MAX_ANALYSIS_CONTEXT_CHARS = 6000               # see the markdown note above


        def func_analyze_with_llm(params: Dict[str, Any]) -> Tuple[bool, dict]:
            question = params.get("question") or ""
            extracted = params.get("extracted_data")

            ctx_obj = extracted
            if isinstance(ctx_obj, str):
                try:
                    ctx_obj = json.loads(ctx_obj)
                except Exception:
                    pass

            context = json.dumps(ctx_obj, indent=2, ensure_ascii=False, default=str)
            if len(context) > MAX_ANALYSIS_CONTEXT_CHARS:
                context = context[:MAX_ANALYSIS_CONTEXT_CHARS] + "\\n…[truncated]"

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
            "Analyze With LLM":       func_analyze_with_llm,
        }
        print(f"Functions registered: {len(FUNCTION_MAP)}")
        for n in FUNCTION_MAP:
            print("  •", n)
    """),

    md("""
        ## §7. Workflow nodes — the LangGraph state machine

        Seven nodes (mirroring `logic/workflow_nodes.py`):

        | Node | Purpose |
        |------|---------|
        | `GoalDefine`        | Persist goal, capture goal-definition metadata |
        | `StrategyPlan`      | Pick a strategy (LLM or `forcedStrategy`), instantiate functions |
        | `FunctionExecute`   | Dispatch the next pending function via `FUNCTION_MAP` |
        | `FunctionValidate`  | Sanity-check function outputs |
        | `StrategyValidate`  | Continue / abort / succeed |
        | `GoalValidate`      | LLM judge — promote `Analysis` to `finalAnswer` if confidence ≥ 0.5 |
        | `done`              | Terminal |
    """),
    md("""
        ### Helpers used across nodes

        Small free functions used by the node implementations below. They are
        the in-notebook equivalent of the public API exposed by the source
        repo's `DatabaseManager` class — same call shapes, same return types,
        just inlined for readability.
    """),
    py("""
        # ---- session-level DB helpers ----------

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

        **Why this node exists**: before we can pick a strategy, we need a
        clear, structured statement of *what the user is asking for*. The
        LLM produces a short JSON blob (description + expected content
        types + key terms) which `node_goal_validate` later uses as the
        rubric for "did we actually answer this?".
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

        Each strategy is a different recipe (LOOKUP for code-keyed queries,
        SEARCH for application-keyed ones, etc.). This node asks the LLM
        which recipe fits the goal, then materialises it into
        `FunctionInSession` rows for the executor.

        If every strategy has been tried, sets `workflowComplete=True` and
        terminates — no infinite loop.
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

        Look up the row, resolve params (query / merged upstream output /
        literal), dispatch to `FUNCTION_MAP`, persist success + outputs.
        `Analyze With LLM`'s `Analysis` is promoted to `state.finalAnswer`.
    """),
    py("""
        # ─── helpers used by node_function_execute ──────────────────────

        def _resolve_params(fid: int, sid: int, fn: str, query: str) -> Dict[str, Any]:
            \"\"\"Read FunctionParametersInSession and fill in actual values.

            Three resolution rules, keyed off `ParameterValue`:
              "Input"  → use the user query directly
              ""       → merge from upstream function outputs in the same strategy
                          (matched by slot name, e.g. "Keyword Output")
              <other>  → literal from §4 (cast to int/json per `Type`)
            \"\"\"
            param_rows = db_query(DB_AGENTIC,
                "SELECT ParameterName, ParameterValue, Type FROM FunctionParametersInSession "
                "WHERE FunctionID = ?", (fid,))
            out: Dict[str, Any] = {}
            for p in param_rows:
                name, val, ptype = p["ParameterName"], p["ParameterValue"], p["Type"]
                if val == "Input":
                    out[name] = query
                elif val == "":
                    # Pull every prior output named `name` in this strategy.
                    merged = collect_outputs(sid, name)
                    # Fallback: a slot literally called "Input" with no upstream
                    # producer should still yield the user query.
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

            # ─── 2-5. Resolve, dispatch, persist, store outputs ──────────
            trace("FunctionExecute", f"{fn}")
            params  = _resolve_params(fid, sid, fn, query)
            handler = FUNCTION_MAP.get(fn)
            if not handler:
                _persist_function_result(fid, fn, sname, False, f"no handler for {fn!r}")
                state["strategyAborted"] = True
                return state
            try:
                success, result = handler(params)
            except Exception as e:
                success, result = False, f"{type(e).__name__}: {e}"
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

        A function can return `success=True` and still write zero output
        rows (e.g. an empty `{}` from a noisy LLM). This node aborts the
        strategy in that case so downstream functions don't chain off
        nothing. Thin by design — strategy-level validation is the next node.
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

        This is the routing decision for the strategy in flight. It looks at
        the strategy's function rows and decides:

        - any failed → **abort** → re-plan
        - all done → **succeed** → goal validation
        - more pending → **continue** → next function
    """),
    py("""
        def node_strategy_validate(state: SessionState) -> SessionState:
            sid = state["currentStrategyID"]
            # One pass over FunctionInSession gives us all four counts —
            # cheaper than four separate COUNT queries.
            stats = db_query(DB_AGENTIC, '''
                SELECT
                  COUNT(*)                                            AS total,
                  SUM(CASE WHEN FunctionSuccess = 1 THEN 1 ELSE 0 END) AS succeeded,
                  SUM(CASE WHEN FunctionSuccess = 0 THEN 1 ELSE 0 END) AS failed,
                  SUM(CASE WHEN FunctionSuccess IS NULL THEN 1 ELSE 0 END) AS pending
                FROM FunctionInSession WHERE StrategyID = ?
            ''', (sid,))[0]
            total, succeeded, failed, pending = (stats["total"], stats["succeeded"] or 0,
                                                 stats["failed"] or 0, stats["pending"] or 0)
            trace("StrategyValidate", f"strategy {sid}: {succeeded}/{total} ok, {pending} pending, {failed} failed")

            # Case 1: any failure aborts the strategy → re-enter StrategyPlan.
            # `strategySatisfied=True` here means "done with this strategy",
            # not "answered the goal" — the abort flag distinguishes them.
            if failed > 0:
                db_exec("UPDATE StrategyInSession SET StrategySuccess = 0, StrategyValidation = ? "
                        "WHERE StrategyID = ?", (f"{failed} function(s) failed", sid))
                state["strategySatisfied"] = True
                state["strategyAborted"]   = True
                return state

            # Case 2: every function done, no failures → forward to GoalValidate.
            if pending == 0:
                db_exec("UPDATE StrategyInSession SET StrategySuccess = 1, StrategyValidation = ? "
                        "WHERE StrategyID = ?", ("all functions ok", sid))
                state["strategySatisfied"] = True
                state["strategyAborted"]   = False
                return state

            # Case 3: still functions to run → loop back to FunctionExecute.
            state["currentFunctionID"] = get_current_function_id(sid)
            state["strategySatisfied"] = False
            state["strategyAborted"]   = False
            return state
    """),

    md("""
        ### `node_goal_validate` — the LLM judge

        The safety gate. The LLM scores the synthesised answer against the
        query + goal definition; only confidence ≥ 0.5 passes. Below that,
        re-enter `node_strategy_plan` and try a different strategy. If all
        strategies fail, the user gets an explicit "no answer" instead of a
        hallucination.

        > **Self-judging caveat**: same model family generates and judges by
        > default; small open models can over-approve. Point
        > `OLLAMA_REASONING` at a stronger model or tighten
        > `PROMPTS["goal_validation"]` if §9.2 shows false approvals.
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

            # ── Resilient confidence extraction ──────────────────────────
            # Small models like llama3.2:3b often respond with prose around
            # the JSON ("Based on the answer, the confidence is 0.85"). We
            # try strict JSON first; if that fails, we regex out any
            # "confidence: 0.X" pattern. If both fail we score 0.0 — but
            # that's now an honest "couldn't parse" rather than a constant
            # rejection that exhausts the recursion budget.
            payload = parse_json_response(judge_resp) or {}
            conf: float = 0.0
            try:
                conf = float(payload.get("confidence", 0.0))
            except (TypeError, ValueError):
                conf = 0.0
            if conf == 0.0:
                m = re.search(r'"?confidence"?\\s*[:=]\\s*([0-9]*\\.?[0-9]+)',
                              judge_resp, flags=re.IGNORECASE)
                if m:
                    try:    conf = float(m.group(1))
                    except: pass
                else:
                    # Last resort: any standalone 0.x number in the output.
                    m2 = re.search(r'\\b0?\\.[0-9]+\\b', judge_resp)
                    if m2:
                        try:    conf = float(m2.group(0))
                        except: pass

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
        ## §8. Build the LangGraph state machine

        Same topology as the source repo. The conditional edge out of
        `StrategyValidate` is the heart of the loop — three possible next
        nodes depending on the strategy state.

        *(diagram below — rendered by `show_mermaid`)*
    """),
    py('''
        show_mermaid(r"""
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
        """)
    '''),
    md("""

        Three places routing branches:

        - **`StrategyPlan`** → `done` *or* `FunctionExecute`
          (do we have any strategies left to try?)
        - **`StrategyValidate`** → `FunctionExecute` *or* `StrategyPlan` *or* `GoalValidate`
          (continue the strategy / give up on it / it's complete)
        - **`GoalValidate`** → `done` *or* `StrategyPlan`
          (the judge is happy / try another strategy)
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
            \"\"\"Wire seven nodes into the state machine.

            Three places where routing branches:

            - StrategyPlan        → done | FunctionExecute
                (any strategies left to try?)
            - StrategyValidate    → FunctionExecute | StrategyPlan | GoalValidate
                (continue / give up on it / strategy complete)
            - GoalValidate        → done | StrategyPlan
                (the judge is happy / try another strategy)
            \"\"\"
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
            # NOTE on `recursion_limit`: in LangGraph 1.0+ this is set on the
            # per-call config dict (passed to `graph.stream(state, config=...)`),
            # NOT on the compiled graph object. See `WORKFLOW_CONFIG` in §9.
            return graph


        graph = build_graph()
        print("graph compiled:", type(graph).__name__)
    """),
    md("""
        ### Render the *actual* compiled graph

        The hand-drawn diagram above stays readable on purpose; the cell below
        dumps the real topology from LangGraph. If they diverge, your edits
        to `build_graph()` changed the shape.
    """),
    py("""
        # Render the compiled graph as Mermaid via show_mermaid (works in Colab).
        try:
            mermaid_src = graph.get_graph().draw_mermaid()
            show_mermaid(mermaid_src)
        except Exception as e:
            # Fall back to a text listing if draw_mermaid is unavailable in this
            # langgraph version, or if the source has chars mermaid.ink chokes on.
            print("(could not render compiled graph:", e, ")")
            print("nodes:", list(graph.get_graph().nodes))
    """),

    md("""
        ## §9. Run a query, end-to-end — with live tracing

        `graph.stream(...)` emits `{node_name: state_after_node}` between
        nodes — useful for watching the workflow evolve. `run_traced(...)`
        wraps that: re-initialises `agentic.db`, streams the graph, prints
        each node that fires (with elapsed time + which `state` fields
        changed), and returns the final state.
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

        # ── Per-call config we hand to graph.stream / graph.invoke ───────
        # In LangGraph 1.0+ the recursion budget is read from this dict on
        # every call, NOT from `compiled_graph.config`. We need enough headroom
        # for ~7 strategies × ~15 graph steps each = ~105 worst-case super-
        # steps before `node_strategy_plan` reaches its "all strategies
        # exhausted" branch. 500 leaves plenty of slack.
        WORKFLOW_CONFIG = {"recursion_limit": 500}


        def run_traced(query: str, *, forced_strategy: Optional[str] = None,
                       verbose_inner: bool = False) -> SessionState:
            \"\"\"Stream the graph for one query, print a per-node trace, return the final state.

            Args:
                query: the natural-language question to answer.
                forced_strategy: if set, bypass `node_strategy_plan`'s LLM
                    selection and force this strategy by name. Useful for
                    debugging a single strategy in isolation (see §9.1).
                verbose_inner: if True, the per-node `trace(...)` calls inside
                    each node also print, on top of the per-node summary line
                    this function emits. Default is `False`, so only the outer
                    (per-node) trace is shown — chatty enough to follow the
                    workflow, quiet enough to read.

            Side effects: re-initialises `agentic.db` at the start of every
            call, so each run begins from a clean slate.
            \"\"\"
            global VERBOSE
            saved, VERBOSE = VERBOSE, verbose_inner          # quieten inner trace() calls
            try:
                init_agentic_db(drop_and_recreate=True)
                populate_template_libraries()

                state = make_session_state(query, forced_strategy=forced_strategy)
                last_seen: Dict[str, Any] = dict(state)
                print(f"❓ query: {query}")
                print(f"   recursion_limit: {WORKFLOW_CONFIG['recursion_limit']}\\n")
                t0 = time.time()
                final: SessionState = state

                for step, update in enumerate(graph.stream(state, config=WORKFLOW_CONFIG), start=1):
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
        ### §9.1 Forced-strategy debug knob

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
        ### §9.2 Failure mode — verify-then-summarise (the safety gate in action)

        Ask for something the catalog doesn't contain. Each strategy retrieves
        real data, the LLM speculates, the judge scores below 0.5,
        `node_strategy_plan` tries another, and once all strategies are
        exhausted the workflow returns "no answer" instead of hallucinating.
        Watch `judgeConfidence < 0.5` and `finalAnswer` flipping to `None`.

        **Expected output** (`llama3.2:3b`, default seeds — your numbers will vary):

        ```
        [01] 🎯 GoalDefine          (+ 1.4s)
               ↳ currentGoalID         = 1
        [02] 🧠 StrategyPlan         (+ 2.7s)
               ↳ currentStrategyID     = 1
               ↳ currentFunctionID     = 1
        …
        [NN] ⚖️  GoalValidate         (+19.8s)
               ↳ judgeConfidence       = 0.20
               ↳ goalSatisfied         = False
               ↳ finalAnswer           = None
        … (re-plan, try a different strategy, judge again, repeat)
        [NN] 🧠 StrategyPlan         (+71.4s)
               ↳ workflowComplete      = True
               ↳ finalAnswer           = 'All strategies exhausted; no satisfactory answer.'
        [NN] 🏁 done                 (+71.4s)

        --- Result ---
          judgeConfidence    0.20
          goalSatisfied      False
          workflowComplete   True
          finalAnswer        All strategies exhausted; no satisfactory answer.
        ```

        if the judge falsely approves, tighten `PROMPTS["goal_validation"]`
        or use a stronger `OLLAMA_REASONING` model.
    """),
    py("""
        final = run_traced("What is the warranty period in months for hose 1071-00-16?")

        print("\\n--- Result ---")
        for k in ("judgeConfidence", "goalSatisfied", "workflowComplete", "finalAnswer"):
            print(f"  {k:18s} {final.get(k)}")
    """),

    md("""
        ### §9.3 Inspecting the persisted execution trace

        Everything the workflow did is in `agentic.db` — the "Relational
        Control Plane" — queryable for audit, debugging, replay.

        > Shows the **most recent run only**: `run_traced(...)` re-initialises
        > `agentic.db` each call. Remove the `init_agentic_db(...)` line in
        > `run_traced` to keep history across runs.
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
        ### §9.4 Interactive Query Widget

        <div class="alert alert-info"><b>Tip:</b> Instead of editing Python variables, use these interactive widgets to test multiple queries seamlessly. It simulates the Layer 3 UI right inside the notebook.</div>
    """),
    py("""
        import ipywidgets as widgets
        from IPython.display import display, clear_output

        # Grab list of strategy names for dropdown
        strategy_names = [s[0] for s in STRATEGIES_SEED]

        query_input = widgets.Textarea(
            value='What is the max working pressure of hose 1071-00-16?',
            placeholder='Type your query...',
            description='Query:',
            disabled=False,
            layout=widgets.Layout(width='80%', height='50px')
        )
        
        strategy_dropdown = widgets.Dropdown(
            options=['Auto (LLM Picks)'] + strategy_names,
            value='Auto (LLM Picks)',
            description='Strategy:',
            disabled=False,
            layout=widgets.Layout(width='50%')
        )

        run_button = widgets.Button(
            description='Run Workflow',
            button_style='primary',
            icon='play'
        )

        output_area = widgets.Output()

        def on_run_clicked(b):
            with output_area:
                clear_output()
                q = query_input.value
                forced_strat = None if strategy_dropdown.value == 'Auto (LLM Picks)' else strategy_dropdown.value
                
                print(f"Running query: {q}")
                if forced_strat:
                    print(f"Forced strategy: {forced_strat}")
                print("-" * 50)
                
                res = run_traced(q, forced_strategy=forced_strat)
                print("\\n" + "=" * 50)
                print("🏁 FINAL ANSWER:")
                print("=" * 50)
                ans = res.get("finalAnswer")
                print(ans if ans else "(no answer — judge rejected)")

        run_button.on_click(on_run_clicked)

        display(widgets.VBox([
            query_input, 
            strategy_dropdown, 
            run_button, 
            output_area
        ]))
    """),

    md("""
        ## Wrap-up — you've finished Layer 2

        Built end-to-end: 9-table schema (§3), 6 strategies + 10 function
        templates seeded (§4), 10 function handlers (§6), multi-tier
        `chat_basic` / `chat_reasoning` / `embed` with retry (§6), 7 LangGraph
        nodes wired through three conditional edges (§7, §8), and the judge
        gate that fails off-catalog queries explicitly instead of
        hallucinating (§9.2).

        ### Lighter than the repo

        - **Functions**: 10 of 15. Missing: `Search Categories`,
          `Aggregate Results`, `Calculate`, `Convert Units`, legacy variants.
        - **Prompts**: inline `PROMPTS` dict + `fmt_prompt`, not YAML +
          `PromptLoader`. Same call shape.
        - **Models**: one chat tier; repo splits `basic` / `reasoning` /
          `multimodal`. Swap via `OLLAMA_MODEL` / `OLLAMA_REASONING` in §1.
        - **Parallel `PlanSteps`** (`[A \\|\\| B]`) omitted — no seeded
          strategy uses it.

        ### Where to push next

        - Wire `Search Products` / `Filter Items` into a strategy (extend
          `STRATEGIES_SEED` and re-run §4).
        - Point `OLLAMA_REASONING` at a bigger model (`phi4`, `qwen2.5:14b`)
          and re-run §9.2 — does the judge tighten up?
        - Compare strategies on one query by setting `forced_strategy`
          per run (§9.1).
    """),

    md("""
        ### Teardown — release the local Ollama process

        If you started Ollama from §1.5b (`ollama_proc` is a `Popen` handle),
        running this cell stops it cleanly so you don't leave a server
        holding GPU memory after the notebook finishes. Safe to skip if
        Ollama was already running before §1.5.
    """),
    py("""
        try:
            if ollama_proc is not None and ollama_proc.poll() is None:
                ollama_proc.terminate()
                ollama_proc.wait(timeout=5)
                print("ollama_proc terminated.")
            else:
                print("Nothing to stop (Ollama was already running, or never started by us).")
        except NameError:
            print("`ollama_proc` not defined — §1.5b was not run in this kernel.")
    """),
]


def main() -> None:
    write_nb(HERE / "02_agentic_reasoning.ipynb", L2_CELLS)

    old = HERE / "02_layer2_agentic_reasoning.ipynb"
    if old.exists():
        old.unlink()
        print(f"removed stale  {old.relative_to(HERE.parent)}")


if __name__ == "__main__":
    main()
