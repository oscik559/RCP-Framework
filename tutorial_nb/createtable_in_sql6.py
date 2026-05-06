import os
import re
import sqlite3
import json
import fitz  # PyMuPDF

# --------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------
db_path = "output.db"
pdf_directory = "Files"

# Set to True if you want to wipe and rebuild the table each run
recreate_table = True

# Regex to match headings like "1", "1.2", "1.2.3.4" possibly with trailing punctuation/spaces
heading_number_pattern = re.compile(r"^\d+(?:\.\d+)*[\.\)]?$")

# --------------------------------------------------------------------
# Helper functions
# --------------------------------------------------------------------

def extract_headings_with_coordinates(page):
    """Return list of {'heading_number', 'heading_name', 'y0', 'y1'} for a page."""
    headings = []
    blocks = page.get_text("blocks")  # (x0, y0, x1, y1, text, block_no, ...)
    blocks.sort(key=lambda b: b[1])  # top‑to‑bottom

    for x0, y0, x1, y1, block_text, *_ in blocks:
        lines = block_text.splitlines()
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if heading_number_pattern.match(line):
                heading_number = line
                heading_name = ""
                # next line in same block could be the title
                if i + 1 < len(lines):
                    nxt = lines[i + 1].strip()
                    if not heading_number_pattern.match(nxt):
                        heading_name = nxt
                        i += 1  # consume it
                headings.append({
                    "heading_number": heading_number,
                    "heading_name": heading_name,
                    "y0": y0,
                    "y1": y1,
                })
            i += 1
    return headings


def find_closest_heading_above(table_y_top, headings):
    """Return heading whose y0 < table top and is closest (largest y0)."""
    candidates = [h for h in headings if h["y0"] < table_y_top]
    return max(candidates, key=lambda h: h["y0"]) if candidates else None


def fill_missing_cells(data):
    """Replace None cells by copying from above, else from left (in‑place)."""
    if not data:
        return
    rows = len(data)
    cols = max(len(r) for r in data)
    for r, row in enumerate(data):
        if len(row) < cols:
            row.extend([None] * (cols - len(row)))
        for c in range(cols):
            if row[c] is None:
                if r > 0 and data[r - 1][c] is not None:
                    row[c] = data[r - 1][c]
                elif c > 0 and row[c - 1] is not None:
                    row[c] = row[c - 1]

# --------------------------------------------------------------------
# Main routine
# --------------------------------------------------------------------

def main():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    tbl = "tables"

    if recreate_table:
        cursor.execute(f"DROP TABLE IF EXISTS [{tbl}];")

    cursor.execute(
        f"""
        CREATE TABLE IF NOT EXISTS [{tbl}] (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filename TEXT,
            page_nr INTEGER,
            heading_number TEXT,
            heading_name TEXT,
            table_name TEXT,
            tablecontent TEXT
        );
        """
    )
    conn.commit()

    pdf_files = [f for f in os.listdir(pdf_directory) if f.lower().endswith(".pdf")]

    for pdf_file_name in pdf_files:
        file_stub = os.path.splitext(pdf_file_name)[0]
        pdf_path = os.path.join(pdf_directory, pdf_file_name)
        doc = fitz.open(pdf_path)
        print(f"\nProcessing {pdf_file_name}")

        for page_idx, page in enumerate(doc, start=1):
            headings = extract_headings_with_coordinates(page)
            tables = page.find_tables().tables
            if not tables:
                print(f"  [!] No tables on page {page_idx}")
                continue
            print(f"  [+] {len(tables)} table(s) on page {page_idx}")
            for t_idx, table in enumerate(tables, start=1):
                y0 = table.bbox[1]
                heading = find_closest_heading_above(y0, headings) or {}
                h_num = heading.get("heading_number", "")
                h_name = heading.get("heading_name", "")
                data = table.extract()
                fill_missing_cells(data)
                table_json = json.dumps(data, ensure_ascii=False)
                tbl_name = f"{file_stub}_p{page_idx}_t{t_idx}"

                cursor.execute(
                    f"INSERT INTO [{tbl}] (filename, page_nr, heading_number, heading_name, table_name, tablecontent)\n                     VALUES (?, ?, ?, ?, ?, ?);",
                    (file_stub, page_idx, h_num, h_name, tbl_name, table_json),
                )
        doc.close()
    conn.commit()
    conn.close()
    print("\nData extraction complete.")


if __name__ == "__main__":
    main()
