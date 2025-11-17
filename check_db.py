import sqlite3

conn = sqlite3.connect('database/agentic.db')
cursor = conn.cursor()

# Count records in each *InSession table
cursor.execute('SELECT COUNT(*) FROM GoalInSession')
goals = cursor.fetchone()[0]
print(f'GoalInSession records: {goals}')

cursor.execute('SELECT COUNT(*) FROM StrategyInSession')
strategies = cursor.fetchone()[0]
print(f'StrategyInSession records: {strategies}')

cursor.execute('SELECT COUNT(*) FROM FunctionInSession')
functions = cursor.fetchone()[0]
print(f'FunctionInSession records: {functions}')

# Show a few session IDs
cursor.execute('SELECT DISTINCT SessionID FROM GoalInSession ORDER BY SessionID DESC LIMIT 10')
sessions = cursor.fetchall()
print(f'\nRecent SessionIDs:')
for s in sessions:
    print(f'  {s[0]}')

conn.close()
