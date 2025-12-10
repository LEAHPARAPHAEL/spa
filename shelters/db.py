import sqlite3
from tabulate import tabulate

# Path to your SQLite database
db_path = "data/shelters.db"   # adjust if different

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


# Count how many rows
cursor.execute(f"SELECT COUNT(*) FROM dogs")
count = cursor.fetchone()[0]
print(f"There are {count} records in table dogs")

# Fetch a few sample entries
cursor.execute(f"SELECT name, breed FROM dogs d JOIN breeds b on d.matched_breed = b.breed_name LIMIT 3")
rows = cursor.fetchall()
print(rows)

cursor.execute(f"SELECT name, image_url FROM dogs d JOIN images i on d.id = i.dog_id LIMIT 3")
rows = cursor.fetchall()
print(rows)

#print("\n Sample rows:")
#print(tabulate(rows, headers=["Name", "Age", "Race", "Size", "URL"], tablefmt="pretty"))

# Close the connection
conn.close()