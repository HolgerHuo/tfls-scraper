# Define here the models for your spider middleware
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/spider-middleware.html

import lxml
from lxml.etree import tostring

class AbsoluteUrlMiddleware:
    def process_response(self, request, response, spider):
        if response.status == 200 and 'text/html' in str(response.headers.get("content-type", "").lower()):
            body_lxml = lxml.html.document_fromstring(response.body)
            for img in body_lxml.xpath('//img'):
                img.set('src',response.urljoin(img.get('src')))
            for attachment in body_lxml.xpath('//a[@class="ke-insertfile"]'):
                attachment.set('href',response.urljoin(attachment.get('href')))
            return response.replace(body=tostring(body_lxml))
        else:
            return response
