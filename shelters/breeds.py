import sqlite3
import csv
import re

csv_file = "data/breeds.csv"
db_file = "data/dogs.db"
table_name = "breeds"

def normalize_header(header):
    """Make header SQLite-friendly: lowercase, replace non-alphanumeric with _"""
    header = header.strip().lower()
    header = re.sub(r'\W+', '_', header)
    return header

def convert_value(value):
    """Try to convert value to float or int, otherwise keep as string"""
    value = value.strip()
    if not value:
        return None
    try:
        if '.' in value:
            return float(value)
        else:
            return int(value)
    except ValueError:
        return value  # keep as string if conversion fails

# Connect to SQLite
conn = sqlite3.connect(db_file)
cur = conn.cursor()

with open(csv_file, newline='', encoding='utf-8') as f:
    reader = csv.reader(f)
    raw_headers = next(reader)
    headers = [normalize_header(h) for h in raw_headers]

    # Create table with TEXT columns first
    columns = ", ".join([f'"{h}" TEXT' for h in headers])
    cur.execute(f'CREATE TABLE IF NOT EXISTS {table_name} ({columns});')

    placeholders = ", ".join(["?"] * len(headers))
    insert_sql = f'INSERT INTO {table_name} ({", ".join(headers)}) VALUES ({placeholders});'

    for row in reader:
        processed_row = [convert_value(v) for v in row]
        cur.execute(insert_sql, processed_row)

conn.commit()
conn.close()
print(f"CSV data imported successfully into {table_name} in {db_file}")