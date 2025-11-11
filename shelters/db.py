import sqlite3
from tabulate import tabulate

# Path to your SQLite database
db_path = "data/dogs.db"   # adjust if different

# Connect to the database
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Check what tables exist
cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
tables = cursor.fetchall()
print("Tables in database:")
for t in tables:
    print("  -", t[0])

print("\n")

# Suppose your table is named 'dogs' (adjust if not)
table_name = "raw_data"


cursor.execute(f"SELECT * FROM breeds LIMIT 3")
rows = cursor.fetchall()
print(rows)

# Count how many rows
cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
count = cursor.fetchone()[0]
print(f"There are {count} records in table '{table_name}'")

# Fetch a few sample entries
cursor.execute(f"SELECT name, age, race, size, url FROM {table_name} LIMIT 10")
rows = cursor.fetchall()

print("\n Sample rows:")
print(tabulate(rows, headers=["Name", "Age", "Race", "Size", "URL"], tablefmt="pretty"))

# Close the connection
conn.close()