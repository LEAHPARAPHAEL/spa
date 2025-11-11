import sqlite3, json, glob

conn = sqlite3.connect("data/shelters.db")
cur = conn.cursor()

# Recreate table if needed
cur.execute("""
CREATE TABLE IF NOT EXISTS dogs (
    id INTEGER PRIMARY KEY,
    name TEXT,
    species TEXT,
    sex TEXT,
    age TEXT,
    race TEXT,
    color TEXT,
    hair TEXT,
    size TEXT,
    description TEXT,
    url TEXT UNIQUE,
    image_urls TEXT
)
""")

for file in glob.glob("data/secondeChance_*.jsonl"):
    print("Loading", file)
    with open(file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                item = json.loads(line)
                cur.execute("""
                INSERT OR IGNORE INTO dogs
                (name, species, sex, age, race, color, hair, size, description, url, image_urls)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item.get("name"),
                    item.get("species"),
                    item.get("sex"),
                    item.get("age"),
                    item.get("race"),
                    item.get("color"),
                    item.get("hair"),
                    item.get("size"),
                    item.get("description"),
                    item.get("url"),
                    ", ".join(item.get("image_urls", []))
                ))
            except json.JSONDecodeError:
                print("⚠️ Invalid JSON line in", file)
conn.commit()
conn.close()
print("Database rebuilt successfully.")