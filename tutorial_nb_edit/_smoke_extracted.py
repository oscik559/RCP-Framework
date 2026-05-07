# === cell 3 ===

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

# === cell 5 ===

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
            "Ollama is not reachable on http://localhost:11434.\n"
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
print("\nFinal Ollama status:", "ready" if ok else "FAILED")
for t in tags:
    print(" •", t)

# === cell 7 ===

def db_query(db_path: str, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
    """Run SELECT, return list of dicts. We'll reuse this everywhere."""
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
print("\nsample lookup 1071-00-16 →", sample)

# === cell 9 ===

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
    """Drop user tables (if asked) and re-create the full schema."""
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

# === cell 11 ===

def inspect_db(db_path: str) -> None:
    """Tree view of tables, columns, and row counts."""
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

# === cell 13 ===

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

# === cell 15 ===

def populate_template_libraries() -> None:
    """Wipe library tables and reseed with constants from §4."""
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

# === cell 16 ===

# Have a look at the strategies you just seeded.
rows = db_query(DB_AGENTIC, '''
    SELECT StrategyID, StrategyName, StrategyTarget,
           substr(StrategyDescription, 1, 60) AS description
    FROM StrategyLibrary ORDER BY StrategyID
''')
for r in rows:
    print(f"  [{r['StrategyID']}] {r['StrategyName']:30s} {r['StrategyTarget']:10s} {r['description']}")

# === cell 19 ===

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

# === cell 21 ===

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
    """Initial state for a new query."""
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
    """Pretty-print the current SessionState — green for set, dim for None."""
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

# === cell 24 ===

# ---- single low-level call --------------------------------------
def ollama_chat(messages: List[Dict[str, str]], temperature: float = 0.0,
                model: str = OLLAMA_MODEL) -> str:
    """POST /api/chat → return content string."""
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
    """Exponential backoff. Re-raise on terminal errors (model not found, etc.)."""
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

# === cell 26 ===

PROMPTS = {
    "goal_definition": {
        "system":
            "You are a goal definition assistant for technical queries about industrial products.\n"
            "Analyze a user query and extract key information that helps validate later answers.\n"
            "Respond with valid JSON only — no preamble.\n\n"
            "Required JSON format:\n"
            "{\n"
            '  "goal_description": "TEXT",\n'
            '  "expected_content_types": ["product_specs", "lookup_values", "..."],\n'
            '  "key_terms": ["pressure", "temperature", "..."],\n'
            '  "success_indicators": ["specific value with units", "source citation", "..."]\n'
            "}",
        "user": "USER QUERY: {query}\n\nAnalyze this query and define the goal.",
    },

    "strategy_selection": {
        "system":
            "You are a strategy-planning assistant for a technical documentation system.\n\n"
            "CRITICAL RULES:\n"
            "• Choose EXACTLY ONE strategy from the AVAILABLE STRATEGIES list.\n"
            "• Use the EXACT strategy name as written (case-sensitive).\n"
            "• You CANNOT choose any from STRATEGIES ALREADY EXECUTED.\n"
            "• You CANNOT invent strategy names.\n\n"
            "Required JSON format:\n"
            '{"StrategyName": "[EXACT name]", "Rationale": "Brief reason"}',
        "user":
            "USER QUERY: {query}\n"
            "GOAL: {goal_desc}\n\n"
            "STRATEGIES ALREADY EXECUTED (forbidden):\n{tried}\n\n"
            "AVAILABLE STRATEGIES (choose exactly one):\n{available}\n\n"
            "Return ONLY valid JSON.",
    },

    "product_code_extraction": {
        "system":
            "You extract COMPLETE product codes from a user query.\n"
            "Preserve every digit and suffix exactly. Output ONLY the codes,\n"
            "comma-separated if multiple. Output empty string if none found.\n"
            "Examples: '1071-00-16' → '1071-00-16'  |  'hose 4201-16-16' → '4201-16-16'",
        "user": "Query: {query}\nProduct codes:",
    },

    "extract_requirements": {
        "system":
            "You extract structured requirements from a user query about hydraulic hoses or couplings.\n"
            "Return JSON only. Leave fields null if not mentioned.\n\n"
            "Schema:\n"
            "{\n"
            '  "application": "hydraulic|water|steam|chemical|...|null",\n'
            '  "pressure_max_bar": <number|null>,\n'
            '  "temperature_max_c": <number|null>,\n'
            '  "diameter_mm": <number|null>,\n'
            '  "keywords": ["term", "term", ...],\n'
            '  "summary": "1-sentence intent"\n'
            "}",
        "user": "Query: {query}\nReturn JSON:",
    },

    "analyze_with_llm": {
        "system":
            "You are a technical analyst for industrial hose and coupling products.\n"
            "Use ONLY the provided product data — no external knowledge.\n"
            "Answer in 1–2 sentences. Include exact values with units. "
            "Cite product_code or family_name. If the data is missing, say so plainly.\n"
            "Match the language of the user's question (Swedish in → Swedish out).",
        "user":
            "PRODUCT DATA:\n{context}\n\n"
            "QUESTION: {question}\n\n"
            "Answer using only the data above:",
    },

    "goal_validation": {
        "system":
            "You evaluate whether the analysis output answers the user's query.\n"
            "Respond with ONLY one JSON object: {\"confidence\": <0.0..1.0>}.\n"
            "No prose, no markdown.\n\n"
            "Scoring:\n"
            "  0.8–1.0  complete answer with specific values\n"
            "  0.6–0.7  good but missing some details\n"
            "  0.3–0.5  partial / insufficient\n"
            "  0.0–0.2  off-topic or no answer\n"
            "If you cannot produce valid JSON, output exactly: {\"confidence\": 0.0}",
        "user":
            "USER QUERY:\n{query}\n\n"
            "GOAL DEFINITION:\n{goal_definition}\n\n"
            "ANALYSIS OUTPUT:\n{evidence}\n\n"
            "Required JSON: {{\"confidence\": 0.0..1.0}}",
    },
}


def fmt_prompt(name: str, **kwargs) -> List[Dict[str, str]]:
    """Build a [system, user] message list for the named prompt."""
    tpl = PROMPTS[name]
    return [
        {"role": "system", "content": tpl["system"]},
        {"role": "user",   "content": tpl["user"].format(**kwargs)},
    ]


def parse_json_response(text: str) -> Optional[dict]:
    """Pull a JSON object out of a noisy LLM response."""
    text = text.strip()
    # Strip ```json fences if present.
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except Exception:
        pass
    m = re.search(r"\{.*\}", text, flags=re.S)
    if m:
        try:
            return json.loads(m.group())
        except Exception:
            return None
    return None


# ---- Mini PromptLoader (mirrors config/prompt_loader.py API) ------
class PromptLoader:
    """Same `format_prompt(category, **kwargs)` API as production."""
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

# === cell 28 ===

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

# === cell 30 ===

def func_extract_product_number(params: Dict[str, Any]) -> Tuple[bool, dict]:
    # Slot "Input" carries the user query (set by the planner at runtime).
    query = params.get("Input", "") or ""

    # Single LLM call — see PROMPTS['product_code_extraction'] for the prompt.
    out = ollama_chat(fmt_prompt("product_code_extraction", query=query))

    # Robustness: take just the first line, strip a leading "Product codes:" if present.
    codes = out.strip().splitlines()[0] if out.strip() else ""
    codes = re.sub(r"^[Pp]roduct codes?:\s*", "", codes).strip().strip('"').strip("'")

    # Output slot name MUST match what's declared in OUTPUTS_SEED for this function.
    return True, {"Keyword Output": codes}

# === cell 32 ===

ok, result = func_extract_product_number({"Input": "What is the working pressure of hose 1071-00-16 vs 4201-16-16?"})
print("ok    :", ok)
print("result:", result)

# === cell 34 ===

def func_extract_requirements(params: Dict[str, Any]) -> Tuple[bool, dict]:
    query = params.get("Input", "") or ""
    out = ollama_chat(fmt_prompt("extract_requirements", query=query))
    data = parse_json_response(out) or {"summary": "(parse failed)", "keywords": []}
    return True, {"requirements": data}

# === cell 36 ===

def _split_codes(s: str) -> List[str]:
    """Split a 'A, B; C\nD' style string into clean codes."""
    if not s:
        return []
    return [p.strip() for p in re.split(r"[,;\n]+", s) if p.strip()]


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

# === cell 38 SKIPPED (runtime/LLM/Chroma) ===

# === cell 40 ===

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

# === cell 42 ===

def func_search_products(params: Dict[str, Any]) -> Tuple[bool, dict]:
    keywords = params.get("keywords", "") or ""
    limit = int(params.get("limit", 20) or 20)

    # Tokenize the user's text. We score families that contain MORE tokens.
    tokens = [t for t in re.split(r"\W+", keywords.lower()) if len(t) > 2]
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

# === cell 44 ===

def func_search_families(params: Dict[str, Any]) -> Tuple[bool, dict]:
    keywords = params.get("keywords", "") or ""
    limit = int(params.get("limit", 20) or 20)

    # Try exact family_code first.
    code_match = re.search(r"\b(\d{4}(?:-\d+)?)\b", keywords)
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

# === cell 46 ===

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

# === cell 48 ===

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
        context = context[:6000] + "\n…[truncated]"

    answer = chat_reasoning(                                    # use the heavier tier for synthesis
        fmt_prompt("analyze_with_llm", context=context, question=question),
        temperature=0.1,
    )
    return True, {"Analysis": answer.strip()}

# === cell 50 ===

COMPARE_PROMPT = {
    "system":
        "You compare two or more product records side-by-side.\n"
        "Return JSON only:\n"
        "{\n"
        '  "comparison_table": {"<field>": ["<val for item1>", "<val for item2>", ...]},\n'
        '  "differences":  ["short bullet", ...],\n'
        '  "similarities": ["short bullet", ...]\n'
        "}\n"
        "Pick fields that genuinely differ where possible.",
    "user":
        "ITEMS:\n{items_json}\n\n"
        "Restrict to these fields if non-empty (otherwise pick interesting ones):\n"
        "{fields_json}\n\n"
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

# === cell 52 ===

def _get_path(d: Any, dotted: str) -> Any:
    """Walk 'a.b.c' through dicts; tolerant of None."""
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

# === cell 54 ===

CONVERT_PROMPT = {
    "system":
        "You are an expert in technical unit conversions.\n"
        "Reply with JSON only:\n"
        '{"converted_value": <number>, "explanation": "<one sentence>"}\n'
        "If the conversion is ambiguous, state the assumption made.",
    "user":
        "Convert {value} {from_unit} to {to_unit}.\n"
        "Context (if any): {context}\n"
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

# === cell 56 ===

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

# === cell 59 ===

# ---- session-level DB helpers (replaces DatabaseManager) ----------

def db_exec(sql: str, params: tuple = ()) -> Optional[int]:
    """Run a write against agentic.db; return lastrowid for inserts."""
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
    """Insert one FunctionInSession row per function name in the plan.
    Then copy the parameter templates into FunctionParametersInSession."""
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
    """Next pending function (FunctionSuccess IS NULL)."""
    rows = db_query(DB_AGENTIC,
        "SELECT FunctionID FROM FunctionInSession "
        "WHERE StrategyID = ? AND FunctionSuccess IS NULL "
        "ORDER BY FunctionID LIMIT 1", (strategy_id,))
    return rows[0]["FunctionID"] if rows else None


def collect_outputs(strategy_id: int, output_name: str) -> List[Any]:
    """Gather all stored outputs of a given name from earlier functions in this strategy."""
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

# === cell 61 ===

class DatabaseManager:
    """Session-scoped wrapper around agentic.db. Same method shape as the production class."""

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
        """Insert FunctionInSession rows for every step (incl. parallel groups)."""
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

# === cell 63 ===

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

# === cell 65 ===

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
            tried="\n".join(f"- {t}" for t in tried) or "- None",
            available="\n".join(f"- {a}" for a in available),
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

# === cell 67 ===

# ─── helpers used by node_function_execute ──────────────────────

def parse_plan_groups(plan_steps: str) -> List[List[str]]:
    """Return the parallel groups in this strategy's PlanSteps."""
    groups: List[List[str]] = []
    for tok in [s.strip() for s in plan_steps.split(",")]:
        if tok.startswith("[") and tok.endswith("]"):
            groups.append([f.strip() for f in tok[1:-1].split("||")])
    return groups


def find_parallel_siblings(sid: int, fn: str) -> Optional[List[int]]:
    """If `fn` is in a parallel group for strategy `sid`, return the FIDs of all pending siblings."""
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
    """Read FunctionParametersInSession and fill in actual values."""
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
    """Update status + store declared outputs."""
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
    """Worker for both sequential and parallel branches."""
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

# === cell 69 ===

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

# === cell 71 ===

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

# === cell 73 ===

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
    evidence = "\n\n---\n\n".join(r["OutputValue"] for r in evidence_rows)

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

# === cell 75 ===

def node_done(state: SessionState) -> SessionState:
    trace("done", f"workflow complete, final answer present: {state.get('finalAnswer') is not None}")
    return state

# === cell 77 ===

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

# === cell 79 SKIPPED (runtime/LLM/Chroma) ===

# === cell 81 SKIPPED (runtime/LLM/Chroma) ===

# === cell 83 SKIPPED (runtime/LLM/Chroma) ===

# === cell 85 SKIPPED (runtime/LLM/Chroma) ===

# === cell 87 SKIPPED (runtime/LLM/Chroma) ===

# === cell 89 ===

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