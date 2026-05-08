"""
Build Layer 1 (Extraction) tutorial notebook.

Run:

    python RCP_notebook/_build_extraction.py
"""
from __future__ import annotations
from pathlib import Path

from _nb_helpers import md, py, write_nb

HERE = Path(__file__).resolve().parent


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

        Notebooks live in `RCP_notebook/` but the project's relative paths
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


def main() -> None:
    write_nb(HERE / "01_layer1_extraction.ipynb", L1_CELLS)


if __name__ == "__main__":
    main()
