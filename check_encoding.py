import sqlite3

conn = sqlite3.connect('database/harvested.db')
cursor = conn.cursor()

# Find all example_value entries with corrupted encoding
cursor.execute('SELECT id, attribute, example_value FROM attribute_glossary WHERE example_value IS NOT NULL')
rows = cursor.fetchall()

corrupted_found = False
for row in rows:
    if 'Ã' in str(row[2]):
        print(f"ID {row[0]:3} | {row[1]:30} | {row[2]}")
        corrupted_found = True

if not corrupted_found:
    print("No encoding issues found in example_value field")

conn.close()
