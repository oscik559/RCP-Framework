import sqlite3

conn = sqlite3.connect('database/harvested.db')
cursor = conn.cursor()

# Check product table
cursor.execute('SELECT id, product_code, configuration_type, configuration_name FROM products WHERE product_code = ?', ('1101-14-06-30',))
products = cursor.fetchall()
print('=== PRODUCTS TABLE ===')
print(f'Found {len(products)} records for 1101-14-06-30')
for row in products:
    print(f'  ID: {row[0]}, Code: {row[1]}, Config Type: {row[2]}, Config Name: {row[3]}')

# Check if there are variants
cursor.execute('SELECT product_code FROM products WHERE product_code LIKE ?', ('1101-14-06%',))
codes = cursor.fetchall()
print(f'\n=== ALL VARIANTS of 1101-14-06 ===')
print(f'Found {len(codes)} variants:')
for code in codes:
    print(f'  - {code[0]}')

conn.close()
