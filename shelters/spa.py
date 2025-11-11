import requests
import json
import time
from pathlib import Path
from datetime import datetime
import sqlite3
import os

BASE_URL = "https://www.la-spa.fr"
PAGE_API = BASE_URL + "/app/wp-json/spa/v1/animals/search/?api=1&species=chien&paged={}"
DOG_API = BASE_URL + "/app/wp-json/spa/v1/posts/?api=1&_uid={}"
DOWNLOAD_DELAY = 1

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

visited_pages_file = CACHE_DIR / "visited_pages.txt"
visited_dogs_file = CACHE_DIR / "visited_dogs.txt"

# Load caches
visited_pages = set(visited_pages_file.read_text().splitlines()) if visited_pages_file.exists() else set()
visited_dogs = set(visited_dogs_file.read_text().splitlines()) if visited_dogs_file.exists() else set()

os.makedirs("data", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
jsonl_file = Path(f"data/spa_{timestamp}.jsonl")

# Database connection
conn = sqlite3.connect("dogs.db")
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS raw_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    url TEXT UNIQUE,
    raw_json TEXT,
    scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
)
""")
conn.commit()

def save_cache(file_path, value):
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(value + "\n")

def fetch_page(page_number):
    url = PAGE_API.format(page_number)
    resp = requests.get(url)
    if resp.status_code != 200:
        print(f"Failed to fetch page {page_number}: {resp.status_code}")
        return None
    return resp.json()

def birthday_to_age(birthday_str: str):
    try:
        # Extract the date part after "le "
        date_part = birthday_str.split("le")[-1].strip()
        birth_date = datetime.strptime(date_part, "%Y-%m-%d").date()
    except Exception as e:
        print(f"Error parsing birthday '{birthday_str}': {e}")
        return None, None

    today = datetime.today().date()

    # Calculate total years and months
    years = today.year - birth_date.year
    months = today.month - birth_date.month
    days = today.day - birth_date.day

    if days < 0:
        months -= 1 

    if months < 0:
        years -= 1
        months += 12

    age_float = years + months / 12
    age_text = (f"{years} ans " if years > 0 else "") + \
                (f"{months} mois" if months > 0 else "")
    age_text = age_text.strip()

    return round(age_float, 2), age_text

def process_dog(dog_json_summary):
    dog_uid = dog_json_summary["uid"]
    if dog_uid in visited_dogs:
        return

    dog_url = DOG_API.format(dog_uid)
    resp = requests.get(dog_url)
    if resp.status_code != 200:
        print(f"Failed to fetch dog {dog_uid}: {resp.status_code}")
        return

    data = resp.json()
    infos = data["content"]["infos"]

    # Collect all images (avoid duplicates)
    image_urls = []
    seen = set()
    for m in infos.get("medias", []):
        if m["type"] == "image" and m["src"] not in seen:
            seen.add(m["src"])
            image_urls.append(BASE_URL + m["src"])

    # Build record
    age, age_text = birthday_to_age(infos.get("birthday", ""))

    record = {
        "source" : "SPA",
        "url": dog_url,
        "name": infos["title"],
        "species": infos["species"]["name"],
        "sex": infos["sex"],
        "age text" : age_text,
        "age" : age,
        "category": infos.get("age", ""),
        "race": ", ".join(r.get("name","") for r in infos.get("races", [])),
        "colors": ", ".join(r for r in infos.get("colors", [])),
        "accepts_children" : infos["accepted"]["child"],
        "accepts_cats" : infos["accepted"]["cat"],
        "accepts_dogs" : infos["accepted"]["dog"],
        "description": infos.get("description", ""),
        "establishment" : data["content"]["establishment"]["tag"]["label"],
        "establishment_url" : data["content"]["establishment"]["url"],
        "images": image_urls,
    }

    with open(jsonl_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")

    # Insert into DB
    cursor.execute("INSERT OR IGNORE INTO raw_data (source, url, raw_json) VALUES (?, ?, ?)",
                   ("spa", record["url"], json.dumps(record, ensure_ascii=False)))
    conn.commit()

    # Mark dog as visited
    visited_dogs.add(dog_uid)
    save_cache(visited_dogs_file, dog_uid)
    print(f"Processed dog {record['name']}")

# Main loop
page_number = 1
while True:
    if str(page_number) in visited_pages:
        print(f"Page {page_number} already visited.")
        page_number += 1
        continue  
    page_json = fetch_page(page_number)
    if not page_json:
        break
    if not page_json.get("results"):
        page_number += 1
        continue  

    for dog_summary in page_json["results"]:
        process_dog(dog_summary)
        time.sleep(DOWNLOAD_DELAY) 

    # Mark page as visited after all dogs are processed
    visited_pages.add(str(page_number))
    save_cache(visited_pages_file, str(page_number))
    print(f"Finished page {page_number}")
    page_number += 1
    time.sleep(DOWNLOAD_DELAY) 

conn.close()

