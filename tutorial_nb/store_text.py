import os
import re
import sqlite3
import fitz  # PyMuPDF

# --------------------------------------------------------------------
# Configuration
# --------------------------------------------------------------------
#pdf_path = "Files/1301-TFR46310.pdf"
db_path = "output.db"
table_name = "text_table"  # We'll store extracted headings/text here
pdf_directory = "Files"


# Regex to match lines like "1", "1.2", "1.2.3.4" possibly with trailing punctuation/spaces
heading_number_pattern = re.compile(r"^\d+(?:\.\d+)*[\.\)]?$")
# You can adjust the pattern above to handle additional punctuation if needed:
# e.g. r"^\d+(?:\.\d+)*[\.:)\s]*$" 
# --------------------------------------------------------------------



# 1) Connect to or create the SQLite database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()



# 2) Create the table for storing heading-based text
create_table_sql = f"""
CREATE TABLE IF NOT EXISTS [{table_name}] (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    document_name TEXT,
    page_number INTEGER,
    heading_number TEXT,
    heading_name TEXT,
    text TEXT
);
"""
cursor.execute(create_table_sql)
conn.commit()


pdf_files = [f for f in os.listdir(pdf_directory) if f.lower().endswith(".pdf")]

for pdf_file_name in pdf_files:
    # e.g. "1301-TFR46310.pdf" -> "1301-TFR46310"
    file_name = os.path.splitext(pdf_file_name)[0]


    pdf_path = os.path.join(pdf_directory, pdf_file_name)
    doc = fitz.open(pdf_path)

    # 3) A helper function to insert a record
    def insert_heading_data(doc_name, page_num, h_num, h_name, txt):
        sql = f"""
        INSERT INTO [{table_name}]
        (document_name, page_number, heading_number, heading_name, text)
        VALUES (?, ?, ?, ?, ?)
        """
        cursor.execute(sql, (doc_name, page_num, h_num, h_name, txt))




    for page_index, page in enumerate(doc, start=1):
        page_text = page.get_text("text")
        lines = page_text.splitlines()
        
        current_heading_number = None
        current_heading_name = None
        collected_text = []

        def save_current_heading():
            """Save the current heading + collected text to DB if there's a heading."""
            if current_heading_number or current_heading_name:
                full_text = "\n".join(collected_text).strip()
                insert_heading_data(file_name, page_index,
                                    current_heading_number or "",
                                    current_heading_name or "",
                                    full_text)

        i = 0
        total_lines = len(lines)

        while i < total_lines:
            line = lines[i].strip()

            # Check if line matches a heading number
            if heading_number_pattern.match(line):
                # If we have an existing heading to save, do it first
                save_current_heading()

                # This line is a heading number
                current_heading_number = line
                current_heading_name = ""
                collected_text = []

                # Look ahead at next line, if any
                if i + 1 < total_lines:
                    next_line = lines[i + 1].strip()
                    # If next_line is NOT another heading, treat it as the heading name
                    if not heading_number_pattern.match(next_line):
                        current_heading_name = next_line
                        i += 1  # consume the next line as heading name
            else:
                # This is body text under the current heading
                collected_text.append(line)

            i += 1

        # After the loop for this page, save whatever heading we have
        save_current_heading()

    doc.close()

# 5) Commit and close
conn.commit()
conn.close()

print("Extraction complete. Headings and text stored in text_table.")
