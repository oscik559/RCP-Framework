# Tutorial Notebooks — Plan

Three step-by-step notebooks, one per layer, that turn the RCP repo into something a new user can read top-to-bottom, run cell-by-cell, and poke at intermediate state. The goal is **discovery and interaction**, not a passive walkthrough — every long-running step should expose something inspectable (a DataFrame, a JSON dump, a saved image, a workflow trace) so the user can stop, look, change, and re-run.

This is a planning document. Once we agree on scope and structure, the actual `.ipynb` files get authored in `tutorial_nb_edit/`.

---

## 0. Decisions to lock in before authoring

These are the choices that shape every notebook — please confirm or redirect on each.

1. **Audience.** Researcher / engineer who has cloned the repo and read the README, but has not yet run anything. Knows Python, may not know LangGraph or VLM pipelines. Notebooks are *not* a substitute for [README.md](../README.md) and [SETUP.md](../SETUP.md) — they assume those got the env to a working state.
2. **Case scope.** Notebooks anchor on **Case I (Hydroscand)** because [database/harvested.db](../database/harvested.db) ships pre-populated and the public PDFs are in the repo. Case II is mentioned as "the same recipe with a different domain" with a pointer, but not re-walked. Confirm or override.
3. **Re-extraction is opt-in, not default.** Layer 1 notebook should *not* re-run the full VLM extraction by default — it would overwrite the shipped DB and require Ollama + qwen2-vl. Default cells **read** the existing DB and **show** what each stage produced; an "Optional: re-run on a new PDF" section at the end has the actual pipeline calls behind a guard flag.
4. **Database safety.** The shipped [database/harvested.db](../database/harvested.db) and [database/agentic.db](../database/agentic.db) are part of the published artefact. Notebook cells that mutate state must either (a) operate on a copy in a tutorial scratch dir, or (b) be clearly gated. Layer 2's `db.clear_all_sessions()` from [main.py](../main.py) is the obvious sharp edge — wrap it.
5. **Execution outputs.** Decide whether committed notebooks ship **with** outputs (heavier diffs, but readers see results without running) or **without** (clean diffs, reader must run). Recommendation: ship *with* outputs for the extraction notebook (slow, requires Ollama) and *without* for L2/L3 (fast enough to run live). Confirm.
6. **LLM dependency for Layer 2.** L2 cells need a working LLM. Default to local Ollama (`llama3.2:latest` + `nomic-embed-text` per [SETUP.md](../SETUP.md)). Add a small "verify Ollama is reachable" cell up front and abort gracefully if not.
7. **Where to put helper code.** Tutorial-only utilities (pretty-printers, DB previewers, image grids) live in a small `tutorial_nb_edit/_helpers.py` so notebook cells stay short and don't drown the narrative. Confirm you want this rather than inlining everything.
8. **Naming.** Suggested filenames:
   - `01_layer1_extraction.ipynb`
   - `02_layer2_agentic_reasoning.ipynb`
   - `03_layer3_user_interface.ipynb`
   Older `Generic_Multiagent_v1.ipynb` and the `tutorial_nb/` siblings get left alone (they're sample/reference). Confirm.

---

## 1. Cross-cutting structure (shared across all three notebooks)

Every notebook opens with the same scaffolding so the experience is consistent:

- **Banner cell.** Title, layer in the architecture diagram, what the reader will produce by the end.
- **Prerequisites cell.** Markdown checklist linking to [SETUP.md](../SETUP.md) and the previous notebook in the chain.
- **Working directory pin.** `os.chdir` to project root if running from `tutorial_nb_edit/`, so all relative paths in the codebase resolve the same way [main.py](../main.py) expects.
- **Environment probe.** Print Python version, key packages (`langgraph`, `chromadb`, `flask`), DB existence, Ollama reachability. One cell, fail-loud if anything's missing.
- **Section headers.** Bold markdown sections matched to a heading in the architecture so the reader can locate "where am I in the pipeline" at a glance.
- **"Try it" callouts.** Every major concept gets a follow-up cell labelled `# Try it:` with one-line tweaks the reader is invited to change (e.g., swap a query, change the debug level, alter a SQL filter). This is the discovery-mode anchor — without these, the notebook becomes a wall of read-only output.
- **Closing cell.** "What you just produced" + "Next notebook: …".

---

## 2. Notebook 1 — `01_layer1_extraction.ipynb` (PDF → harvested.db)

**Anchor file**: [Layer_1_Extraction/Case_I/Layer_1b/](../Layer_1_Extraction/Case_I/Layer_1b/) and its [README](../Layer_1_Extraction/Case_I/Layer_1b/README.md).

**Story arc**: a PDF catalog goes through six stages and ends up as queryable rows in `harvested.db`. The reader sees what every stage produces.

| Section | What the cells do | Interactive payoff |
|---------|-------------------|--------------------|
| Intro & architecture | Show the Layer 1b ASCII diagram, list the three source PDFs in [Layer_1b/](../Layer_1_Extraction/Case_I/Layer_1b/) | None — context only |
| Inspect a source PDF | Use PyMuPDF to render and display 2-3 pages from `Produktbok_2020.pdf` inline | Reader can change the page index |
| Stage 0 — knowledge extraction | Show what `0_extract_knowledge.py` produced: query `product_knowledge` table, group by `knowledge_type`, render one assembly-instruction record | Reader picks a different `knowledge_type` |
| Stage 1 — PDF→PNG | Walk `data/png_pages/`, display a thumbnail grid. Skip if folder absent (note: shipped repo may not include rendered PNGs) | Reader picks a page to enlarge |
| Stage 2 — page regions | Query `page_regions`, overlay header/footer boxes on the PNG of one page using matplotlib | Reader changes the page |
| Stage 2b/3a — categories & families | Query `categories` and `product_families`, show as DataFrames; pick one family and show its products | Reader filters by category |
| Stage 3b — product VLM extraction | Query `products`, show row count, language distribution, a few full rows expanded as JSON | Reader writes a small SQL query |
| FTS5 demo | Run a `MATCH` query against the FTS index | Reader changes the search term |
| Optional: re-run on a new PDF | Guarded section with `RERUN_EXTRACTION = False`. When True, runs scripts 0→3b in order, with timing | Reader flips the flag if they have Ollama + a PDF |
| Validation | Call out to `python database/db_utils.py --verify` via `!` magic | Read-only |

**Things to consider**:
- Several stage scripts are CLI entry points expecting `--pdf` / `--all`. Either import their main functions where they exist, or drive via `subprocess` / `!` magic. Note up front which is which.
- Display of Swedish text needs UTF-8; the [main.py](../main.py:24-27) Windows reconfigure pattern should be the first cell.
- Don't accidentally hammer Ollama in every read-only cell — VLM calls are the slow ones, only invoke them in the gated re-run section.

---

## 3. Notebook 2 — `02_layer2_agentic_reasoning.ipynb` (the RCP control loop)

**Anchor files**: [main.py](../main.py), [Layer_2_Agentic_Reasoning/](../Layer_2_Agentic_Reasoning/), [docs/graph.png](../docs/graph.png).

**Story arc**: a natural-language query enters the LangGraph state machine, traverses Goal → Strategy → Function → Verify, and emerges as a validated answer. The reader sees state evolve at each step instead of just the final printout that [main.py](../main.py) gives.

| Section | What the cells do | Interactive payoff |
|---------|-------------------|--------------------|
| Architecture orientation | Embed [docs/graph.png](../docs/graph.png), list the six stages of the verify-then-summarise loop | Context |
| Session state primer | Call `get_default_session_state()` from [session_config.py](../Layer_2_Agentic_Reasoning/config/session_config.py), pretty-print the dict, annotate each field | Reader changes the seed query |
| Template & prompt loading | Run `populate_template_libraries()`; introspect what got loaded (counts of strategies, function specs) | Reader inspects one strategy template |
| The state graph | Build the graph via `get_graph()`, render its node/edge structure (LangGraph's `.get_graph().draw_mermaid()` or similar), match node names to [docs/graph.md](../docs/graph.md) | Reader views the Mermaid source |
| Quick run, end-to-end | Run a single canonical query (e.g., the boiling-water hose query from [main.py:63](../main.py#L63)) with `debug_level=2`. Capture the full final state | Reader swaps in their own query |
| Inspect intermediate state | Use `graph.stream(...)` (LangGraph streaming API) instead of `.invoke()` to print state after each node — currentGoalID, currentStrategyID, currentFunctionID, judgeConfidence | Reader picks a different verbosity |
| Strategies in detail | Pull strategy rows from `agentic.db`, show how a chosen strategy decomposes into functions | Reader flips `forcedStrategy` to bypass selection |
| Function library tour | List functions from [logic/function_library.py](../Layer_2_Agentic_Reasoning/logic/function_library.py), call one in isolation (e.g., a SQL retrieval function) with hand-picked args | Reader calls a different function |
| Failure modes | Run a query designed to fail validation; show how the loop surfaces an explicit failure rather than hallucinating | Reader designs a failing query |
| Multi-language | Run the Swedish query example from [main.py:71](../main.py#L71-L72) | Reader writes their own |
| Cleanup | Call the wrapped `clear_all_sessions()` only on a tutorial-scoped session DB copy | Safe by construction |

**Things to consider**:
- The `clear_all_sessions()` call in [main.py:103](../main.py#L103) wipes `agentic.db`. In a tutorial context this is hostile to "stop, look, re-run" — wrap it so it only clears sessions tagged with the tutorial's session prefix, or operate on a copy of `agentic.db` placed in `tutorial_nb_edit/scratch/`.
- LangGraph's `recursion_limit: 1000000` from [session_config.py:106](../Layer_2_Agentic_Reasoning/config/session_config.py#L106) is fine for prod but means a buggy strategy could spin forever in a notebook. Consider lowering for tutorial cells.
- Streaming intermediate state is the most important interactive payoff in this notebook. If LangGraph's stream API doesn't expose what we want, fall back to a small custom callback / patched node wrapper.
- Many of the nodes log via the `debug_config` module — surface that as a "turn the dial up" cell rather than burying it.

---

## 4. Notebook 3 — `03_layer3_user_interface.ipynb` (Flask + progress events)

**Anchor files**: [run_web.py](../run_web.py), [Layer_3_User_Interface/web_app.py](../Layer_3_User_Interface/web_app.py), [Layer_3_User_Interface/README.md](../Layer_3_User_Interface/README.md), [Layer_3_User_Interface/templates/index.html](../Layer_3_User_Interface/templates/index.html).

**Story arc**: how Layer 2 gets exposed to a browser. The reader inspects the Flask app, hits the API from inside the notebook, watches a progress stream, and sees the rendered UI.

| Section | What the cells do | Interactive payoff |
|---------|-------------------|--------------------|
| What this layer does | Embed the Layer 3 ASCII diagram from [its README](../Layer_3_User_Interface/README.md), explain the three endpoints | Context |
| Inspect the Flask app | Import `app` from `web_app`, list routes via `app.url_map`, show the templated `index.html` rendered as raw HTML | Reader maps endpoints to handlers |
| Start the server in a background thread | Run the Flask dev server in a non-blocking thread on port 5001 (or a tutorial-only port to avoid clashes); poll `/` to confirm it's up | Reader changes the port |
| Submit a query via HTTP | Use `requests.post('/query', ...)` to fire the same query from notebook 2; receive a session ID | Reader changes the query |
| Stream progress events | Consume the SSE stream from `/progress/<session_id>`, print each event as it arrives so the reader sees the same step-by-step trace as notebook 2 — this time over the wire | Reader watches a slow query in real time |
| Fetch the final result | `GET /result/<session_id>` and pretty-print the JSON | Reader compares vs. notebook 2's in-process result |
| Live UI | Print a clickable link to `http://127.0.0.1:5001` and an `IFrame` embed of the running app | Reader uses the actual UI |
| Configuration tour | Walk the env vars (`SECRET_KEY`, `FLASK_DEBUG`) and the model settings in [config_loader.py](../Layer_2_Agentic_Reasoning/config/config_loader.py) — same ones [SETUP.md §9](../SETUP.md) covers | Reader edits debug verbosity |
| Shutdown | Stop the server thread cleanly | Always runs at end |

**Things to consider**:
- A background-thread Flask server is fine for a notebook but make shutdown bullet-proof — a leaked port is the #1 reader complaint. Consider `werkzeug.serving.make_server` with an explicit `.shutdown()` call rather than `app.run`.
- `IFrame` embedding only works in classic Jupyter/JupyterLab; in VS Code's notebook viewer it may show a placeholder. Print the URL prominently so the reader can open it in a real browser regardless.
- Server-Sent Events: `requests` doesn't stream by default — use `stream=True` and iterate `response.iter_lines()`, or use `httpx`/`sseclient`. Pick one and stick with it.
- The web app calls into Layer 2 on startup and may take several seconds; the "is it up?" poll cell needs a generous timeout.
- Don't expose the app on `0.0.0.0` from inside a notebook — bind to `127.0.0.1` only.

---

## 5. Open questions for you

Please answer or redirect on each before I author the notebooks:

1. **Case scope** — confirm "Case I only, Case II as a pointer" (§0.2)? --use case 1 since the data is available online also. but use already extracted db as backup.
2. **Outputs in committed notebooks** — ship L1 with outputs, L2 + L3 without (§0.5)? yes
3. **Helper module** — OK to add `tutorial_nb_edit/_helpers.py` (§0.7)? - everything should be in the respective notbooks. yes -helpers is fine
4. **Filenames** — `01_…`, `02_…`, `03_…` as proposed (§0.8)? yes
5. **Layer 1 re-run section** — is the gated `RERUN_EXTRACTION = False` opt-in the right default (§2)? decide
6. **Streaming intermediate state in L2** — is this the most important payoff for you, or would you rather emphasise something else (e.g., comparing strategies side-by-side, or the function library)? we are using one case 1
7. **Server in a notebook for L3** — happy with the background-thread approach, or would you prefer the notebook only show client code that talks to a server the reader started in a separate terminal? background threads okay. any preferable. advise
8. **Anything missing** — concepts you've added late in development that aren't covered above (e.g., domain-agnostic config switching, parallel execution mode, the `forcedStrategy` override) and want highlighted as first-class tutorial topics?


make sure to add direct comments and make intuitive