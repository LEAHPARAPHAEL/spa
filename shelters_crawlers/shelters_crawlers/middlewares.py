# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import scrapy
# useful for handling different item types with a single interface
from itemadapter import ItemAdapter
import os
import logging
from urllib.parse import urlparse


class SheltersCrawlersSpiderMiddleware:
    # Not all methods need to be defined. If a method is not defined,
    # scrapy acts as if the spider middleware does not modify the
    # passed objects.

    @classmethod
    def from_crawler(cls, crawler):
        # This method is used by Scrapy to create your spiders.
        s = cls()
        crawler.signals.connect(s.spider_opened, signal=signals.spider_opened)
        return s

    def process_spider_input(self, response, spider):
        # Called for each response that goes through the spider
        # middleware and into the spider.

        # Should return None or raise an exception.
        return None

    def process_spider_output(self, response, result, spider):
        # Called with the results returned from the Spider, after
        # it has processed the response.

        # Must return an iterable of Request, or item objects.
        for i in result:
            yield i

    def process_spider_exception(self, response, exception, spider):
        # Called when a spider or process_spider_input() method
        # (from other spider middleware) raises an exception.

        # Should return either None or an iterable of Request or item objects.
        pass

    async def process_start(self, start):
        # Called with an async iterator over the spider start() method or the
        # maching method of an earlier spider middleware.
        async for item_or_request in start:
            yield item_or_request

    def spider_opened(self, spider):
        spider.logger.info("Spider opened: %s" % spider.name)


class SheltersCrawlersDownloaderMiddleware:
    def url2filename(self, url):
        path = url.replace("https://","")
        if path=="" or path[-1] == "/":
            path = path + "ROOT"
        return "cache/" + path

    def process_request(self, request, spider):
        if request.method != "GET":
            return None

        if urlparse(request.url).scheme == "file":
           return None

        filename = self.url2filename(request.url)
        if os.path.isfile(filename):
            logging.info("Getting "+request.url+" from "+filename)
            with open(filename, "rb") as inf:
                response=inf.read()
            return scrapy.http.TextResponse(body=response, url=request.url,
                                            request=request)
        else:
            # Continue processing
            return None

    def process_response(self, request, response, spider):
        filename = self.url2filename(request.url)

        if not os.path.isfile(filename):
            os.makedirs(os.path.dirname(filename), exist_ok=True)
            logging.info("Storing "+request.url+" into "+filename)
            with open(filename, "wb") as out:
                out.write(response.body)
        return response
