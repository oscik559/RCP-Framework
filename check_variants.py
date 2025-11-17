import sqlite3
conn = sqlite3.connect('database/harvested.db')
cursor = conn.cursor()

# Check exact product
cursor.execute('SELECT id, product_code, configuration_name FROM products WHERE product_code = ?', ('1101-14-06-30',))
result = cursor.fetchone()
print('=== EXACT MATCH: 1101-14-06-30 ===')
if result:
    print(f'ID: {result[0]}, Code: {result[1]}, Config: {result[2]}')
else:
    print('NOT FOUND')

# Check base product
cursor.execute('SELECT id, product_code, configuration_name FROM products WHERE product_code = ?', ('1101-14-06',))
result = cursor.fetchone()
print('\n=== BASE PRODUCT: 1101-14-06 ===')
if result:
    print(f'ID: {result[0]}, Code: {result[1]}, Config: {result[2]}')
else:
    print('NOT FOUND')

# Show all 1101-14-06* variants
cursor.execute('SELECT product_code, configuration_name FROM products WHERE product_code LIKE ? ORDER BY product_code', ('1101-14-06%',))
rows = cursor.fetchall()
print(f'\n=== ALL 1101-14-06 VARIANTS ({len(rows)}) ===')
for code, config in rows:
    print(f'  - {code:20} (config: {config})')

conn.close()
