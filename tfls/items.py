# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy

class PageItem(scrapy.Item):
    file_urls = scrapy.Field()
    files = scrapy.Field()
    description = scrapy.Field()
    tags = scrapy.Field()
    date = scrapy.Field()
    author = scrapy.Field()
    url = scrapy.Field()
    slug = scrapy.Field()
    title = scrapy.Field()
    content = scrapy.Field()
    categories = scrapy.Field()
    path = scrapy.Field()
    weight = scrapy.Field()