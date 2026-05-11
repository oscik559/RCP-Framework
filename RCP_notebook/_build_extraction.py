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

        > 🔗 [github.com/oscik559/RCP-Framework](https://github.com/oscik559/RCP-Framework) — full source, additional cases, eval suites.

        The RCP framework targets **technical documentation** that fits a
        *Categories → Families → Items* shape. This notebook walks the
        **extraction pipeline** that turns a sample of that documentation —
        a Swedish-language Hydroscand product catalog — into the structured
        SQLite database `database/harvested.db` that the rest of the
        framework queries. Layer 2 ([02_agentic_reasoning.ipynb](./02_agentic_reasoning.ipynb))
        is the brain that answers questions over what this notebook builds.

        **Default mode is read-only.** The shipped `harvested.db` is already
        populated, so cells below *inspect* what each stage produced. To
        re-run the full pipeline against a fresh PDF, flip the
        `RERUN_EXTRACTION` flag in §8.

        > **Run the next cell first** — every diagram below calls `show_mermaid(...)` (mermaid.ink renders the SVG inline; works in Jupyter, VS Code, and Colab).
    """),
    py("""
        # Pin CWD to project root, configure UTF-8, import the helpers we use everywhere.
        import sys
        sys.path.insert(0, str(__import__("pathlib").Path.cwd()))  # so _helpers.py imports
        from _helpers import (
            pin_project_root, configure_utf8_stdout, env_probe,
            query, show_query, pdf_page_image,
            show_mermaid, inspect_db, display_product_spec,
        )

        ROOT = pin_project_root()
        configure_utf8_stdout()
        print("project root:", ROOT)
    """),

    md("""
        ### Pipeline at a glance

        Six stages, each writing into a specific table. Stages 0/1/2 only
        read the PDF; stages 2b/3a/3b are VLM-driven.

        *(diagram below — rendered by `show_mermaid`)*
    """),
    py('''
        show_mermaid(r"""
        flowchart LR
            P([PDFs]) --> S0[Stage 0<br/>extract_knowledge]
            P --> S1[Stage 1<br/>pdf_to_png]
            S1 --> S2[Stage 2<br/>headers/footers]
            S2 --> S2b[Stage 2b<br/>categories]
            S2b --> S3a[Stage 3a<br/>families]
            S3a --> S3b[Stage 3b<br/>products + JSON specs]

            S0 --> KT[(product_knowledge)]
            S2 --> RG[(page_regions)]
            S2b --> CT[(categories)]
            S3a --> PF[(product_families<br/>+ FTS)]
            S3b --> PR[(products)]

            style S2b fill:#fff3cd,stroke:#856404
            style S3a fill:#fff3cd,stroke:#856404
            style S3b fill:#fff3cd,stroke:#856404
        """)
    '''),

    md("""
        ### Source-repo crosswalk

        Every section here corresponds to a script in
        [`Layer_1_Extraction/Case_I/Layer_1b/`](https://github.com/oscik559/RCP-Framework/tree/main/Layer_1_Extraction/Case_I/Layer_1b).

        | Stage | Source script | Notebook section |
        |-------|---------------|------------------|
        | 0     | [`0_extract_knowledge.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_1_Extraction/Case_I/Layer_1b/0_extract_knowledge.py)    | [§3](#stage-knowledge) |
        | 1     | [`1_pdf_to_png.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_1_Extraction/Case_I/Layer_1b/1_pdf_to_png.py)              | [§4](#stage-pdf-to-png) |
        | 2     | [`2_detect_headers_footers.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_1_Extraction/Case_I/Layer_1b/2_detect_headers_footers.py) | [§5](#stage-regions) |
        | 2b    | [`2b_extract_categories.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_1_Extraction/Case_I/Layer_1b/2b_extract_categories.py) | [§6](#stage-categories) |
        | 3a    | [`3a_extract_families.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_1_Extraction/Case_I/Layer_1b/3a_extract_families.py) | [§6](#stage-categories) |
        | 3b    | [`3b_extract_products_vlm.py`](https://github.com/oscik559/RCP-Framework/blob/main/Layer_1_Extraction/Case_I/Layer_1b/3b_extract_products_vlm.py) | [§7](#stage-products) |
        | —     | [`database/db_utils.py`](https://github.com/oscik559/RCP-Framework/blob/main/database/db_utils.py)              | [§9](#section-validate) |
    """),

    md("""
        ### Notebook map and inventory

        | § | Title | What you do |
        |---|-------|-------------|
        | [§0](#section-setup)            | Setup                       | Pin CWD, configure stdout, env probe |
        | [§0.5](#section-colab)          | Colab — mount Drive         | Skip on local |
        | [§1](#section-pdfs)             | The source PDFs             | List + render a page |
        | [§2](#section-knowledge)        | Stage 0 — knowledge         | `product_knowledge` |
        | [§3](#stage-pdf-to-png)         | Stage 1 — PDF → PNG         | rasterised pages |
        | [§4](#stage-regions)            | Stage 2 — page regions      | `page_regions` |
        | [§5](#stage-categories)         | Stages 2b / 3a              | `categories` + `product_families` |
        | [§6](#stage-products)           | Stage 3b — products         | `products` + JSON specs |
        | [§7](#section-search)           | Lexical search              | `LIKE` over `product_families` |
        | [§8](#section-rerun)            | Optional re-run             | full pipeline against a fresh PDF |
        | [§9](#section-validate)         | Validate the database       | `inspect_db` over `harvested.db` |

        Tables in `harvested.db` (counts vary with the shipped DB):

        | Table | Source stage | Holds |
        |-------|--------------|-------|
        | `product_knowledge`  | 0     | Prose: assembly, standards, ToCs |
        | `page_regions`       | 2     | Header/footer bboxes per page |
        | `categories`         | 2b    | Top-level catalog buckets |
        | `product_families`   | 3a    | Product families + applications |
        | `product_families_fts` | 3a  | FTS5 index over family text |
        | `products`           | 3b    | One row per SKU, JSON spec blob |
        | `product_knowledge_fts` | 0  | FTS5 index over knowledge prose |
    """),

    md("""
        <a id="section-setup"></a>
        ## §0. Setup — environment probe

        <div class="alert alert-warning"><b>Action Required:</b> If anything below
        is marked <code>MISSING</code>, fix it before continuing — later cells will
        fail.</div>
    """),
    py("""
        # Reachable Python deps + databases. Pass check_ollama=True to also probe Ollama.
        for k, v in env_probe(check_ollama=False).items():
            print(f"{k:30s} {v}")
    """),
    md("""
        <div class="alert alert-success"><b>Checkpoint:</b> If
        <code>database/harvested.db</code> shows a non-zero KB above, you can
        run the rest of the notebook end-to-end.</div>
    """),

    md("""
        <a id="section-colab"></a>
        ### §0.5 Colab only — mount Google Drive (skip on local)

        If you've put `RCP_notebook/` in your Google Drive, run the next cell
        to mount Drive and `cd` into the folder. On a local Jupyter / VS Code
        session this is a no-op.
    """),
    py("""
        # Mount Google Drive and cd into the notebook folder when on Colab.
        import os
        import sys

        if "google.colab" in sys.modules:
            from google.colab import drive
            drive.mount("/content/drive")

            # Edit if you put RCP_notebook/ somewhere other than the Drive root.
            DRIVE_PATH = "/content/drive/MyDrive/RCP_notebook"

            if os.path.isdir(DRIVE_PATH):
                os.chdir(DRIVE_PATH)
                # Re-pin to project root after the chdir.
                ROOT = pin_project_root()
                print(f"cwd → {os.getcwd()}; project root → {ROOT}")
            else:
                print(f"⚠️  Not found: {DRIVE_PATH}")
                print("   Edit DRIVE_PATH above, or upload RCP_notebook/ to the Drive root.")
        else:
            print("Not on Colab — Drive mount skipped.")
    """),

    md("""
        <a id="section-pdfs"></a>
        ## §1. The source PDFs

        Three Swedish-language Hydroscand PDFs ship alongside the extraction
        scripts. They are publicly available from Hydroscand, so swap in your
        own copy if these change.
    """),
    py("""
        from pathlib import Path

        PDF_DIR = Path("Layer_1_Extraction/Case_I/Layer_1b")
        PDFS = sorted(PDF_DIR.glob("*.pdf"))
        for pdf in PDFS:
            kb = pdf.stat().st_size // 1024
            print(f"{pdf.name:30s} {kb:>6} KB")
    """),

    md("""
        ### Render a page inline

        PyMuPDF (`fitz`) is a project dep. Use the widget below to flip
        through any page of any PDF without re-editing the cell.
    """),
    py("""
        # Interactive PDF page viewer. Falls back to plain variables on
        # kernels without ipywidgets (e.g. some headless / GitHub previews).
        from IPython.display import display

        try:
            import ipywidgets as widgets

            pdf_dropdown = widgets.Dropdown(
                options=[(p.name, p) for p in PDFS],
                description="PDF:",
                layout=widgets.Layout(width="50%"),
            )
            page_slider = widgets.IntSlider(
                value=8, min=0, max=200, step=1, description="page (0-based):",
                continuous_update=False,
                layout=widgets.Layout(width="50%"),
            )
            out = widgets.Output()

            def _render(*_):
                out.clear_output(wait=True)
                with out:
                    display(pdf_page_image(pdf_dropdown.value, page_slider.value, dpi=110))

            pdf_dropdown.observe(_render, names="value")
            page_slider.observe(_render, names="value")
            display(widgets.VBox([widgets.HBox([pdf_dropdown, page_slider]), out]))
            _render()
        except ImportError:
            # Plain-variable fallback.
            PDF_NAME, PAGE_INDEX = "Produktbok_2020.pdf", 8
            display(pdf_page_image(PDF_DIR / PDF_NAME, PAGE_INDEX, dpi=110))
            print("(install ipywidgets to get a page slider)")
    """),

    md("""
        <a id="section-knowledge"></a>
        ## §2. Stage 0 — knowledge extraction

        `0_extract_knowledge.py` reads catalog intro pages (assembly
        instructions, standards, ToCs) into `product_knowledge`. These rows
        carry **prose** — the kind of text the reasoning agent later cites
        when an answer needs context beyond a row of numbers.

        <div class="alert alert-warning"><b>Heads-up:</b> in the shipped
        <code>harvested.db</code>, <code>product_knowledge</code> is empty
        (the prose layer was set aside in the published artefact). The cells
        below will report 0 rows — re-run Stage 0 (§8) to populate it.</div>
    """),
    py("""
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
        <a id="stage-pdf-to-png"></a>
        ## §3. Stage 1 — PDF → PNG

        `1_pdf_to_png.py` rasterises every page so downstream stages can run
        a Vision Language Model on them. Rendered PNGs are gitignored — if
        the folder is empty, that's expected.
    """),
    py("""
        from IPython.display import Image, display

        png_dir = Path("Layer_1_Extraction/Case_I/Layer_1b/data/png_pages")
        if not png_dir.exists() or not any(png_dir.glob("*.png")):
            print(f"{png_dir} not present (or empty) — re-run Stage 1 to populate.")
        else:
            pngs = sorted(png_dir.glob("*.png"))
            print(f"{len(pngs)} rendered pages. Showing the first one inline:")
            display(Image(filename=str(pngs[0]), width=480))
    """),

    md("""
        <a id="stage-regions"></a>
        ## §4. Stage 2 — page regions

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
        <a id="stage-categories"></a>
        ## §5. Stages 2b / 3a — categories and families

        Stage 2b extracts top-level categories (e.g. SPIRALSLANG). Stage 3a
        groups products into families that share specs (e.g. hose family
        4201). Together they're the "shape" of the catalog.
    """),
    py("""
        show_query(DB, "SELECT id, name, chapter, page_number FROM categories ORDER BY name LIMIT 20", max_col=80)
    """),
    md("""
        ### Browse families inside a category

        Pick any category name from the list above to see the families it
        contains. The dropdown is populated from the live DB.
    """),
    py("""
        # Interactive category → families browser. Falls back to a hard-coded
        # CAT variable if ipywidgets isn't installed.
        from IPython.display import display

        _, cat_rows = query(DB, "SELECT name FROM categories ORDER BY name")
        cat_names = [r[0] for r in cat_rows]

        def _show_families(cat: str) -> None:
            show_query(DB, '''
                SELECT pf.family_code, pf.name AS family_name, pf.description
                FROM product_families pf
                JOIN categories c ON c.id = pf.category_id
                WHERE c.name = ?
                ORDER BY pf.family_code
                LIMIT 15
            ''', (cat,))

        try:
            import ipywidgets as widgets

            cat_dropdown = widgets.Dropdown(
                options=cat_names,
                value="HÖGTRYCKSSLANG" if "HÖGTRYCKSSLANG" in cat_names else cat_names[0],
                description="category:",
                layout=widgets.Layout(width="60%"),
            )
            out = widgets.Output()

            def _render(change):
                out.clear_output(wait=True)
                with out:
                    _show_families(change["new"] if isinstance(change, dict) else cat_dropdown.value)

            cat_dropdown.observe(_render, names="value")
            display(cat_dropdown, out)
            _render({"new": cat_dropdown.value})
        except ImportError:
            CAT = "HÖGTRYCKSSLANG"
            _show_families(CAT)
            print("\\n(install ipywidgets for a category dropdown)")
    """),

    md("""
        <a id="stage-products"></a>
        ## §6. Stage 3b — products (the actual SKUs)

        Each row in `products` is one SKU with a JSON spec blob. The blob is
        what the reasoning engine ultimately quotes from when answering a
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
    md("""
        ### Look up one product

        Type a `product_code` from the table above. Rendering uses
        `display_product_spec` from `_helpers.py` so the cell stays short.
    """),
    py("""
        # Interactive product lookup with a search button. Falls back to a
        # hard-coded PRODUCT_CODE if ipywidgets isn't installed.
        from IPython.display import display

        try:
            import ipywidgets as widgets

            code_input = widgets.Text(
                value="1071-00-16",
                placeholder="product_code",
                description="code:",
                layout=widgets.Layout(width="40%"),
            )
            go_btn = widgets.Button(description="Show spec", button_style="primary")
            out = widgets.Output()

            def _on_click(_):
                out.clear_output(wait=True)
                with out:
                    display_product_spec(DB, code_input.value.strip())

            go_btn.on_click(_on_click)
            display(widgets.HBox([code_input, go_btn]), out)
            _on_click(None)
        except ImportError:
            PRODUCT_CODE = "1071-00-16"
            display_product_spec(DB, PRODUCT_CODE)
            print("\\n(install ipywidgets for an input box + search button)")
    """),

    md("""
        <a id="section-search"></a>
        ## §7. Lexical search over family applications

        The pipeline also builds FTS5 indexes (`product_families_fts`,
        `product_knowledge_fts`) — these are what Layer 2 strategies hit
        when a query needs keyword search before semantic re-ranking.

        <div class="alert alert-info"><b>Note:</b> the shipped FTS5 index is
        contentless, so we use a plain <code>LIKE</code> over the same
        columns here. The behaviour is similar enough for tutorial
        purposes; for the real thing, see Layer 2 §6 (Chroma-backed
        Semantic Search).</div>
    """),
    py("""
        # Interactive search box. Falls back to a hard-coded Q on kernels
        # without ipywidgets.
        from IPython.display import display

        def _do_search(q: str) -> None:
            if not q.strip():
                print("(empty query)")
                return
            show_query(DB, '''
                SELECT family_code, name, applications
                FROM product_families
                WHERE applications LIKE ? OR description LIKE ? OR name LIKE ?
                ORDER BY family_code
                LIMIT 10
            ''', (f"%{q}%", f"%{q}%", f"%{q}%"), max_col=80)

        try:
            import ipywidgets as widgets

            q_input = widgets.Text(
                value="tryck",
                placeholder='try "tryck", "boiling", "marin"',
                description="query:",
                layout=widgets.Layout(width="60%"),
            )
            search_btn = widgets.Button(description="Search", button_style="primary")
            out = widgets.Output()

            def _on_search(_):
                out.clear_output(wait=True)
                with out:
                    _do_search(q_input.value)

            search_btn.on_click(_on_search)
            q_input.on_submit(lambda _: _on_search(None))
            display(widgets.HBox([q_input, search_btn]), out)
            _on_search(None)
        except ImportError:
            Q = "tryck"
            _do_search(Q)
            print("\\n(install ipywidgets for a search box)")
    """),

    md("""
        <a id="section-rerun"></a>
        ## §8. Optional — re-run extraction on a fresh PDF

        Everything above was read-only. Flip the flag below to actually run
        the extraction scripts. You need:

        - **Ollama** running locally (`ollama serve`)
        - The vision model: `ollama pull qwen2-vl`
        - Plenty of patience — Stage 3b alone runs the VLM on every page

        <div class="alert alert-danger"><b>⚠️ Destructive:</b> re-running
        overwrites the shipped <code>database/harvested.db</code>. To keep
        the original, copy it aside first:
        <code>cp database/harvested.db database/harvested.db.backup</code>.</div>
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
        <a id="section-validate"></a>
        ## §9. Validate the database

        Same shape as `inspect_db()` in 02_agentic_reasoning.ipynb — every
        table in `harvested.db`, with row counts and column lists. Treat it
        as the canonical "is the DB sane?" check.
    """),
    py("""
        inspect_db(DB)
    """),

    md("""
        ## Wrap-up — you've finished Layer 1

        - The PDF → DB pipeline is six stages, each writing into one table.
        - The shipped database is enough to drive every Layer 2 / Layer 3 demo.
        - Re-extraction is opt-in; default is read-only inspection.

        **Next:** [02_agentic_reasoning.ipynb](./02_agentic_reasoning.ipynb) —
        the reasoning engine that queries this DB to answer
        natural-language questions.
    """),
]


def main() -> None:
    write_nb(HERE / "01_layer1_extraction.ipynb", L1_CELLS)


if __name__ == "__main__":
    main()
