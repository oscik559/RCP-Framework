import sqlite3

conn = sqlite3.connect('database/agentic.db')
cursor = conn.cursor()

# Delete all records from session tables to start fresh
print("Clearing old session data...")
cursor.execute('DELETE FROM FunctionOutputInSession')
print("✅ Cleared FunctionOutputInSession")

cursor.execute('DELETE FROM FunctionParametersInSession')
print("✅ Cleared FunctionParametersInSession")

cursor.execute('DELETE FROM FunctionInSession')
print("✅ Cleared FunctionInSession")

cursor.execute('DELETE FROM StrategyInSession')
print("✅ Cleared StrategyInSession")

cursor.execute('DELETE FROM GoalInSession')
print("✅ Cleared GoalInSession")

conn.commit()
conn.close()

print("\n✅ Database cleaned! All old session data removed.")
print("Each new query will now start with a clean slate.")
