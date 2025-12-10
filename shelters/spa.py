import requests
import json
import time
from pathlib import Path
from datetime import datetime
import sqlite3
import os
import re
import html

BASE_URL = "https://www.la-spa.fr"
PAGE_API = BASE_URL + "/app/wp-json/spa/v1/animals/search/?api=1&species=chien&paged={}&seed=224145464626602"
DOG_API = BASE_URL + "/app/wp-json/spa/v1/posts/?api=1&_uid={}"
DOWNLOAD_DELAY = 1

CACHE_DIR = Path("cache")
CACHE_DIR.mkdir(exist_ok=True)

visited_pages_file = CACHE_DIR / "spa_visited_pages.txt"
visited_dogs_file = CACHE_DIR / "spa_visited_dogs.txt"

# Load caches
visited_pages = set(visited_pages_file.read_text().splitlines()) if visited_pages_file.exists() else set()
visited_dogs = set(visited_dogs_file.read_text().splitlines()) if visited_dogs_file.exists() else set()

os.makedirs("data", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
jsonl_file = Path(f"data/spa.jsonl")

breeds = json.load(open("data/breeds_mapping.json", "r"))["spa"]

# Database connection
conn = sqlite3.connect("data/shelters.db")
cursor = conn.cursor()
cursor.execute("""
    CREATE TABLE IF NOT EXISTS dogs (
        id INTEGER PRIMARY KEY,
        source TEXT,
        name TEXT,
        url TEXT UNIQUE,
        species TEXT,
        sex TEXT,
        age_text TEXT,
        age REAL,
        category TEXT,
        breed TEXT,
        matched_breed TEXT,
        colors TEXT,
        accepts_dogs BOOL,
        accepts_cats BOOL,
        accepts_children BOOL,
        establishment TEXT, 
        establishment_url TEXT
    )
    """)

cursor.execute("""
    CREATE TABLE IF NOT EXISTS images (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        dog_id INTEGER,
        image_url TEXT,
        FOREIGN KEY (dog_id) REFERENCES dogs (id) ON DELETE CASCADE
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
        try:
            birth_date = datetime.strptime(date_part, "%d/%m/%Y").date()
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
    age_text = (f"{years} years " if years > 0 else "") + \
                (f"{months} months" if months > 0 else "")
    age_text = age_text.strip()

    return round(age_float, 2), age_text

def sex_to_english(sex):
    if not sex:
        return None
    sex = re.sub("Femelle", "Female", sex)
    sex = re.sub("Mâle", "Male", sex)

    return sex

def clean_dog_name(name):
    name = html.unescape(name)
    pattern = r"(\s*\(.*|\s*&.*|\s+\bQCN\b.*|\s+\bVAA\b.*|\s+\w*\d{5}.*)"
    
    # Replace the matching pattern with an empty string
    cleaned_name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    return cleaned_name.strip()

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

    url = data.get("seo_link", {}).get("canonical", dog_url)

    # Collect all images (avoid duplicates)
    image_urls = []
    seen = set()
    for m in infos.get("medias", []):
        if m["type"] == "image" and m["src"] not in seen:
            seen.add(m["src"])
            image_urls.append(BASE_URL + m["src"])

    # Build record
    age, age_text = birthday_to_age(infos.get("birthday", ""))

    races = [r.get("name",None) for r in infos.get("races", [])]
    if len(races) > 0:
        breed = races[0]
        matched_breed = breeds.get(breed.lower(), {}).get("matched_breed", None)
    else:
        breed = None
        matched_breed = None

    colors = [r for r in infos.get("colors", [])]
    if colors:
        colors = ", ".join(colors)
    else:
        colors = None

    sex = infos.get("sex", None)
    sex = sex_to_english(sex)

    item = {
        "source" : "SPA",
        "url": url,
        "name": clean_dog_name(infos["title"]),
        "species": infos["species"]["name"],
        "sex": sex,
        "age_text" : age_text,
        "age" : age,
        "category": infos.get("age", None),
        "breed": breed,
        "matched_breed" : matched_breed,
        "colors": colors,
        "accepts_children" : infos["accepted"]["child"],
        "accepts_cats" : infos["accepted"]["cat"],
        "accepts_dogs" : infos["accepted"]["dog"],
        #"description": infos.get("description", ""),
        "establishment" : data["content"]["establishment"]["tag"]["label"],
        "establishment_url" : data["content"]["establishment"]["url"],
        "image_urls": image_urls,
    }

    with open(jsonl_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(item, ensure_ascii=False) + "\n")

    # Insert into DB
    cursor.execute("""
                INSERT OR IGNORE INTO dogs
                (source, name, url, species, sex, age_text, age, category, breed, matched_breed, colors, accepts_dogs, accepts_cats, accepts_children, establishment, establishment_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "SPA",
                    item.get("name"),
                    item.get("url"),
                    item.get("species"),
                    item.get("sex"),
                    item.get("age_text"),
                    item.get("age"),
                    item.get("category"),
                    item.get("breed"),
                    item.get("matched_breed"),
                    item.get("colors"),
                    item.get("accepts_dogs"),
                    item.get("accepts_cats"),
                    item.get("accepts_children"),
                    item.get("establishment"),
                    item.get("establishment_url")
                ))
    
    current_dog_id = cursor.lastrowid
                                            
    images = item.get("image_urls", [])
                                
    if images and current_dog_id:
        image_data = [(current_dog_id, img_url) for img_url in images]
                                        
        cursor.executemany("""
            INSERT INTO images (dog_id, image_url) 
            VALUES (?, ?)
        """, image_data)

    conn.commit()

    # Mark dog as visited
    visited_dogs.add(url)
    save_cache(visited_dogs_file, url)
    print(f"Processed dog {item['name']}")

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

