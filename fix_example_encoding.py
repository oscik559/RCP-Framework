import sqlite3

conn = sqlite3.connect('database/harvested.db')
cursor = conn.cursor()

# Map of corrupted → correct values
fixes = {
    'HÃ–GTRYCKSSLANG': 'HÖGTRYCKSSLANG',
    'KAPITEL 1:1 HÃ–GTRYCKSSLANG': 'KAPITEL 1:1 HÖGTRYCKSSLANG',
    'PÃ… BOBIN': 'PÅ BOBIN',
    'Olje- och nÃ¶tningsbestÃ¤ndigt polyuretan': 'Olje- och nötningsbeständigt polyuretan',
    'Ett flÃ¤tat polyesterinlÃ¤gg': 'Ett flätat polyesterinlägg',
    'Svart hÃ¶lje, prickklad': 'Svart hölje, prickklad',
}

for corrupted, correct in fixes.items():
    cursor.execute('UPDATE attribute_glossary SET example_value = ? WHERE example_value = ?', 
        (correct, corrupted))
    print(f"Fixed: {corrupted} → {correct}")

conn.commit()
print('\n✅ Fixed all encoding issues in example_value field')
conn.close()
