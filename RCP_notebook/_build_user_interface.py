"""
Build Layer 3 (User Interface) tutorial notebook.

Run:

    python RCP_notebook/_build_user_interface.py
"""
from __future__ import annotations
from pathlib import Path

from _nb_helpers import md, py, write_nb

HERE = Path(__file__).resolve().parent


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
    write_nb(HERE / "03_layer3_user_interface.ipynb", L3_CELLS)


if __name__ == "__main__":
    main()
