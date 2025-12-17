import requests
import json
import time
from pathlib import Path
from datetime import datetime
import sqlite3
import os
import re
import html


class SPA_spider:

    def __init__(self):
        super().__init__()

        os.makedirs("data", exist_ok=True)

        # Base URL
        self.base_url = "https://www.la-spa.fr"

        # The records are obtainable by page number, and regroup several dogs
        # Note that we need to fix the seed, to ensure reproducibility, otherwise each access shuffles the dogs.
        self.page_api = self.base_url + "/app/wp-json/spa/v1/animals/search/?api=1&species=chien&paged={}&seed=224145464626602"
        self.dog_api = self.base_url + "/app/wp-json/spa/v1/posts/?api=1&_uid={}"
        self.download_delay = 1

        # Path indicating where to store the page indices and dogs ids that have been processed.
        self.cache_dir = Path("cache")
        self.cache_dir.mkdir(exist_ok=True)

        self.visited_dogs_file = self.cache_dir / "spa_visited_urls.txt"

        # Load cache
        self.visited_dogs = set(self.visited_dogs_file.read_text().splitlines()) if self.visited_dogs_file.exists() else set()

        self.jsonl_file = Path(f"data/spa.jsonl")

        # Breeds mapping to try to identify the breed of a dog from its french name.
        self.breeds = json.load(open("data/breeds_mapping.json", "r"))["spa"]

        # French dictionary used to clean the dog's name
        self.french_dictionary = self.load_french_dictionary("data/french_dictionary.txt")


    def connect_to_database(self):
        # Connects to the database
        self.conn = sqlite3.connect("data/shelters.db")
        self.cur = self.conn.cursor()

        # Creates the tables in the database if not already existing
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS dogs (
                id INTEGER PRIMARY KEY,
                source TEXT,
                name TEXT,
                url TEXT UNIQUE,
                adopted BOOL,
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

        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS images (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dog_id INTEGER,
                image_url TEXT,
                FOREIGN KEY (dog_id) REFERENCES dogs (id) ON DELETE CASCADE
            )
            """)

        self.conn.commit()


    # Gets the json file from the API by replacing the placeholder field by the correct page number
    def fetch_page(self, page_number):
        url = self.page_api.format(page_number)
        resp = requests.get(url)
        if resp.status_code != 200:
            print(f"Failed to fetch page {page_number}: {resp.status_code}")
            return None
        return resp.json()
    

    # Main method parsing the SPA database page by page
    def parse_spa(self):

        self.connect_to_database()

        # Iterates through all pages in SPA
        page_number = 1

        # Keeps track of following empty pages to stop the loop if we reach the end.
        # The problem is that somehow, the pages do exist, but do not contain anything.
        empty_pages = 0

        while True:
            page_json = self.fetch_page(page_number)
            if not page_json or empty_pages >= 5:
                break
            if not page_json.get("results"):
                page_number += 1
                empty_pages += 1
                continue  
            
            # Found page, so reset counter to 0
            empty_pages = 0
            for dog_summary in page_json["results"]:
                dog_uid = dog_summary["uid"]
                dog_uid_clean = dog_uid.replace("animal-", "")

                url = self.base_url + f"/animal/{dog_uid_clean}/"

                if url in self.visited_dogs:
                    continue
                self.process_dog(dog_summary, url)
                time.sleep(self.download_delay) 

            # Mark page as visited after all dogs are processed
            print(f"Finished page {page_number}")
            page_number += 1
            time.sleep(self.download_delay) 


    def process_dog(self, dog_json_summary, url):

        dog_uid = dog_json_summary["uid"]

        # Inserts the id into the placeholder field to get the url for this dog.
        dog_api_url = self.dog_api.format(dog_uid)

        resp = requests.get(dog_api_url)

        if resp.status_code != 200:
            print(f"Failed to fetch dog {dog_uid}: {resp.status_code}")
            return

        data = resp.json()

        # Part of the JSON file where the infos are stored
        infos = data["content"]["infos"]

        # Gets the URL
        #url = data.get("seo_link", {}).get("canonical", dog_api_url)

        # Collect all images (avoid duplicates)
        image_urls = []
        seen = set()
        for m in infos.get("medias", []):
            if m["type"] == "image" and m["src"] not in seen:
                seen.add(m["src"])
                image_urls.append(self.base_url + m["src"])

        
        # Gets the age and converts it to both float and text 
        age, age_text = self.birthday_to_age(infos.get("birthday", ""))

        # Identifies the breed in the races list
        races = [r.get("name",None) for r in infos.get("races", [])]
        if len(races) > 0:
            breed = races[0]

            # Tries to find a match against a breed from the dataset
            matched_breed = self.breeds.get(breed.lower(), {}).get("matched_breed", None)
        else:
            breed = None
            matched_breed = None

        # Looks for potential colors in the corresponding fields 
        # (always empty in practice, I don't know why it exists in the first place in the JSON file)

        colors = [r for r in infos.get("colors", [])]
        if colors:
            colors = ", ".join(colors)
        else:
            colors = None

        sex = infos.get("sex", None)
        sex = self.sex_to_english(sex)

        # Builds the record
        item = {
            "source" : "SPA",
            "url": url,
            "name": self.clean_dog_name(infos["title"], self.french_dictionary),
            "adopted" : False,
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

        # Saves the record as a new line of the jsonl file
        with open(self.jsonl_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

        # Inserts the new record into the database
        self.cur.execute("""
            INSERT OR IGNORE INTO dogs
            (source, name, url, adopted, species, sex, age_text, age, category, breed, matched_breed, colors, accepts_dogs, accepts_cats, accepts_children, establishment, establishment_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "SPA",
                item.get("name"),
                item.get("url"),
                item.get("adopted"),
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
        
        # Gets the last row id to use as a foreign key in the images table
        current_dog_id = self.cur.lastrowid
                                                
        images = item.get("image_urls", [])
                                    
        if images and current_dog_id:
            image_data = [(current_dog_id, img_url) for img_url in images]
                                            
            self.cur.executemany("""
                INSERT INTO images (dog_id, image_url) 
                VALUES (?, ?)
            """, image_data)

        self.conn.commit()

        # Marks dog as visited
        self.visited_dogs.add(url)
        self.save_cache(self.visited_dogs_file, url)
        print(f"Processed dog {item['name']}")


    
    def save_cache(self, file_path, value):
        with open(file_path, "a", encoding="utf-8") as f:
            f.write(value + "\n")


    def load_french_dictionary(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                vocab_set = {line.strip().lower() for line in f if line.strip()}
                
            return vocab_set
            
        except:
            raise(Exception("Problem loading the dictionary."))

    def clean_dog_name(self, raw_text, dictionary_set):
        if not raw_text or not isinstance(raw_text, str):
            return None

        # Avoids characters like html rsquo
        text = html.unescape(raw_text)

        # Regex pattern
        pattern = r"^([^\W\d_]|[\s\-'’])+"
        match = re.match(pattern, text)
        
        if not match:
            return None
            
        # Takes the first part before the occurrence of the first non alphabetical character
        cleaned_name = match.group(0).strip()

        # Removes weird patterns that are specific to the two shelters, especially SPA
        pattern = r"(\-|\s*\(.*|\s*&.*|\s+\bQCN\b.*|\s+\bVAA\b.*|\s+\bCHAO\b.*|\s+\w*\d{5}.*)"
        
        # Replaces the matching pattern with an empty string
        cleaned_name = re.sub(pattern, "", cleaned_name, flags=re.IGNORECASE)
        
        tokens = cleaned_name.split()
        
        if not tokens:
            return None

        # Checks if some french word artefacts are still present in the name
        is_french_word = []
        for token in tokens:

            token_clean = token.lower().strip("-'’")
            
            # Check if in dictionary
            is_french_word.append(token_clean in dictionary_set)

        # If all the words are potentially french words, we have to output everything, because
        # we cannot be sure.
        if all(is_french_word):
            return cleaned_name.title()
        else:
            final_tokens = []
            for word, is_french in zip(tokens, is_french_word):
                if not is_french:
                    final_tokens.append(word)
                    
            return " ".join(final_tokens).title()



    def birthday_to_age(self, birthday_str: str):
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

    def sex_to_english(self, sex):
        if not sex:
            return None
        sex = re.sub("Femelle", "Female", sex)
        sex = re.sub("Mâle", "Male", sex)

        return sex



if __name__ == "__main__":
    
    spa_spider = SPA_spider()

    spa_spider.parse_spa()