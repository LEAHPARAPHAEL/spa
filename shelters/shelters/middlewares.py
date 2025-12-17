# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

from itemadapter import ItemAdapter
import os
import scrapy
import logging
import hashlib
from urllib.parse import urlparse
from scrapy import signals
from scrapy.http import TextResponse
from scrapy.exceptions import IgnoreRequest

class SheltersSpiderMiddleware:
    # Avoids recrawling already seen urls
    def __init__(self, cache_dir="cache", visited_file="seconde_chance_visited_urls.txt"):
        self.cache_dir = cache_dir
        self.visited_file = os.path.join(cache_dir, visited_file)
        self.visited = set()

        os.makedirs(self.cache_dir, exist_ok=True)

        # Loads previously seen URLs
        if os.path.isfile(self.visited_file):
            with open(self.visited_file, "r", encoding="utf-8") as f:
                for line in f:
                    self.visited.add(line.strip())

    @classmethod
    def from_crawler(cls, crawler):
        middleware = cls()
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def spider_closed(self, spider):
        # Writes the visited urls in a txt file
        with open(self.visited_file, "w", encoding="utf-8") as f:
            for url in sorted(self.visited):
                f.write(url + "\n")
        spider.logger.info(f"Saved {len(self.visited)} visited URLs to {self.visited_file}")

    def _url_to_path(self, url):
        parsed = urlparse(url)
        safe_name = hashlib.md5(url.encode("utf-8")).hexdigest()
        folder = os.path.join(self.cache_dir, parsed.netloc)
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, safe_name + ".html")

    def process_request(self, request, spider):
        if request.method != "GET":
            return None

        if request.url in self.visited and request.url.startswith("https://www.secondechance.org/animal/chien"):
            print(request.url)
            spider.logger.debug(f"Skipping already visited URL: {request.url}")
            raise IgnoreRequest()

        return None

    def process_response(self, request, response, spider):
        if request.method != "GET" or response.status != 200:
            return response

        self.visited.add(request.url)
        return response
