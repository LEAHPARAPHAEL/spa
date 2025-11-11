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
    """Downloader middleware that caches responses on disk and avoids re-crawling known URLs."""

    def __init__(self, cache_dir="cache", visited_file="seconde_chance_visited_urls.txt"):
        self.cache_dir = cache_dir
        self.visited_file = os.path.join(cache_dir, visited_file)
        self.visited = set()

        os.makedirs(self.cache_dir, exist_ok=True)

        # Load previously seen URLs
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
        """Persist visited URLs to disk when spider closes."""
        with open(self.visited_file, "w", encoding="utf-8") as f:
            for url in sorted(self.visited):
                f.write(url + "\n")
        spider.logger.info(f"Saved {len(self.visited)} visited URLs to {self.visited_file}")

    def _url_to_path(self, url):
        """Generate a deterministic file path from the URL."""
        parsed = urlparse(url)
        # Hash long URLs to avoid filesystem issues
        safe_name = hashlib.md5(url.encode("utf-8")).hexdigest()
        folder = os.path.join(self.cache_dir, parsed.netloc)
        os.makedirs(folder, exist_ok=True)
        return os.path.join(folder, safe_name + ".html")

    def process_request(self, request, spider):
        """Serve response from cache if available, otherwise let Scrapy fetch it."""
        if request.method != "GET":
            return None

        if request.url in self.visited and request.url.startswith("https://www.secondechance.org/animal/chien"):
            print(request.url)
            spider.logger.debug(f"Skipping already visited URL: {request.url}")
            raise IgnoreRequest()

        '''
        # Serve from cache if it exists
        if os.path.isfile(filepath):
            spider.logger.debug(f"Serving from cache: {request.url}")
            with open(filepath, "rb") as f:
                body = f.read()
            self.visited.add(request.url)
            return TextResponse(
                url=request.url,
                body=body,
                encoding="utf-8",
                request=request
            )
        '''

        return None

    def process_response(self, request, response, spider):
        """Save new responses to cache and record visited URL."""
        if request.method != "GET" or response.status != 200:
            return response

        '''
        # Good during testing but will be removed afterwards.
        filepath = self._url_to_path(request.url)
        if not os.path.isfile(filepath):
            with open(filepath, "wb") as f:
                f.write(response.body)
            spider.logger.debug(f"Cached new page: {filepath}")
        '''

        self.visited.add(request.url)
        return response
