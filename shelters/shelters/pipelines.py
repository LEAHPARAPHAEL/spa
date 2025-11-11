# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html


# useful for handling different item types with a single interface
import json
import sqlite3
from datetime import datetime
import os

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


class SQLitePipeline:
    def open_spider(self, spider):
        os.makedirs("data", exist_ok=True) 
        self.conn = sqlite3.connect("data/dogs.db")
        self.cur = self.conn.cursor()
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_data (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                url TEXT UNIQUE,
                raw_json TEXT,
                scraped_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.commit()

    def process_item(self, item, spider):
        import json
        self.cur.execute("""
            INSERT OR REPLACE INTO raw_data (source, url, raw_json)
            VALUES (?, ?, ?)
        """, (
            spider.name, 
            item.get("url"), 
            json.dumps(dict(item), ensure_ascii=False)
        ))
        self.conn.commit()
        return item

    def close_spider(self, spider):
        self.conn.close()
