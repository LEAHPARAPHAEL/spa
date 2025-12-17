# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import json
import sqlite3
from datetime import datetime
import os

# This is called automatically by Scrapy when yielding a new record
# It stores every new record in the seconde_chance.jsonl file.
class JsonWriterPipeline:

    def open_spider(self, spider):
        os.makedirs("data", exist_ok=True)
        self.filename = "data/seconde_chance.jsonl"
        mode = "a" if os.path.exists(self.filename) else "w"
        self.file = open(self.filename, mode, encoding="utf-8")

        if mode == "a":
            spider.logger.info(f"Appending to existing file {self.filename}")
        else:
            spider.logger.info(f"Creating new file {self.filename}")

    def process_item(self, item, spider):
        line = json.dumps(dict(item), ensure_ascii=False)
        self.file.write(line + "\n")
        return item

    def close_spider(self, spider):
        self.file.close()
        spider.logger.info(f"Finished writing to {self.filename}")


# THis is called automatically by the spider, and stores every new record
# on the fly in the database.
class SQLitePipeline:
    def open_spider(self, spider):
        os.makedirs("data", exist_ok=True) 
        self.conn = sqlite3.connect("data/shelters.db")
        self.cur = self.conn.cursor()
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

    def process_item(self, item, spider):
        self.cur.execute("""
            INSERT OR IGNORE INTO dogs
            (source, name, url, adopted, species, sex, age_text, age, category, breed, matched_breed, colors, accepts_dogs, accepts_cats, accepts_children, establishment, establishment_url)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                "Seconde chance",
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
            )
        )

        current_dog_id = self.cur.lastrowid
                                
                                
        images = item.get("image_urls", []) 
                                
        if images and current_dog_id:
            image_data = [(current_dog_id, img_url) for img_url in images]
                                        
            self.cur.executemany("""
                INSERT INTO images (dog_id, image_url) 
                VALUES (?, ?)
            """, image_data)

        self.conn.commit()
        return item

    def close_spider(self, spider):
        self.conn.close()
