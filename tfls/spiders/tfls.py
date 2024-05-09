import scrapy
from scrapy.spiders import CrawlSpider
from ..items import PageItem

import requests
from hashlib import md5

class TflsSpider(CrawlSpider):
    name = "tfls"
    allowed_domains = ["tfls.tj.edu.cn"]

    pages_with_sidebars = [
        {'name': '校园概况', 'url': 'http://tfls.tj.edu.cn/html/school/'},
        {'name': '管理机构', 'url': 'http://tfls.tj.edu.cn/html/institution/'},
        {'name': '教学科研', 'url': 'http://tfls.tj.edu.cn/html/research/'},
        {'name': '学生之窗', 'url': 'http://tfls.tj.edu.cn/html/students/'},
        {'name': '国际课程', 'url': 'http://tfls.tj.edu.cn/html/international/'},
        {'name': '师资队伍', 'url': 'http://tfls.tj.edu.cn/html/teachers/'},
        {'name': '党政工团', 'url': 'http://tfls.tj.edu.cn/html/partypolicy/'},
        {'name': '校务公开', 'url': 'http://tfls.tj.edu.cn/html/publicaffair/'},
        {'name': '培训中心', 'url': 'http://tfls.tj.edu.cn/html/tcenter/'},
        {'name': '公开招聘', 'url': 'http://tfls.tj.edu.cn/html/recruitment/'},
        {'name': '新闻中心', 'url': 'http://tfls.tj.edu.cn/html/news/'},
        {'name': '育人特色', 'url': 'http://tfls.tj.edu.cn/html/moral/'},
        {'name': '校友之家', 'url': 'http://tfls.tj.edu.cn/html/alumni/'},
        {'name': '对外交流', 'url': 'http://tfls.tj.edu.cn/html/external/'},
        #{'name': '招生信息', 'url': 'http://tfls.tj.edu.cn/html/admission/'}
    ]

    pages = [
        {'name': '名师风采', 'url': 'http://tfls.tj.edu.cn/html/teachers/master/'},
        {'name': '优秀学子', 'url': 'http://tfls.tj.edu.cn/html/students/master/'},
        {'name': '历任校长', 'url': 'http://tfls.tj.edu.cn/html/single/principals.html'}
    ]

    def start_requests(self):
        for page in self.pages_with_sidebars:
            yield scrapy.Request(page['url'], self.parse_sidebar)
        for page in self.pages:
            yield scrapy.Request(page['url'], self.parse)

        yield scrapy.Request(url="http://xsc.tfls.tj.edu.cn/micro/zsbm/ann/pageForLogin", method='POST',body=r'param=%7B%22page%22%3A1%2C%22pageSize%22%3A6%7D', headers={'Accept': 'application/json, text/plain, */*', 'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'},callback=self.parse_xsc)

    def parse_sidebar(self, response):
        yield from response.follow_all(xpath='//div[@id="vertmenu"]/ul/li/a', callback=self.parse)

    def parse(self, response):
        self.logger.info(f"Found: {response.url}")
        if not response.xpath('//div[@id="content_div"]').get():
            yield from response.follow_all(xpath='//td[@class="a03"]//a', callback=self.parse)
            if response.xpath('//a[text()="下一页"]/text()').get() == '下一页':
                yield response.follow(response.xpath('//a[text()="下一页"]/@href')[0].get(), callback=self.parse)
        else:
            page = PageItem()
            page['url'] = response.url
            page['title'] = response.xpath('//div[@id="lm-top01"]/h4/text()').get() or response.xpath('//h2[@id="title_h2"]/text()').get()
            meta = response.xpath('//h5[@id="public_h5"]/text()').get() 
            if meta:
                try:
                    author, date = meta.split('  发布日期：')
                    page['author'] = author.replace('来源：', '')
                    page['date'] = f"{date[0:10]}T00:00:00+08:00"
                except:
                    pass
            page['content'] = response.xpath('//div[@id="content_div"]').get()
            url_slugs = response.url.rsplit('/')
            page['slug'] = url_slugs[-1].replace('.html', '')
            page['path'] = '/'.join(url_slugs[url_slugs.index('html')+1:-1])
            if page['path'] != 'principals' and response.xpath('//div[@id="lm-top02"]/text()').get():
                page['categories'] = [response.xpath('//div[@id="lm-top02"]//a[2]/text()').get()] if response.xpath('//div[@id="lm-top02"]//a[2]/text()').get() else None
                page['tags'] = [response.xpath('//div[@id="lm-top02"]//a[3]/text()').get()] if response.xpath('//div[@id="lm-top02"]//a[3]/text()').get() else None
            sidebar = [item.replace('· ', '') for item in response.xpath('//div[@id="vertmenu"]/ul/li/a/text()').getall()] if response.xpath('//div[@id="vertmenu"]/ul/li/a/text()').getall() else None
            if sidebar and page['title'] in sidebar:
                sequence = ['school','teachers','institution']
                page['weight'] = sidebar.index(page['title']) + 1 + (sequence.index(page['path']) +1)*100 if page['path'] in sequence else sidebar.index(page['title']) + 1 
            if page['url'] == 'http://tfls.tj.edu.cn/html/single/principals.html':
                page['weight'] = 200
            page['file_urls'] = []
            for url in response.xpath('//div[@id="content_div"]//img/@src').extract():
                if 'www.tfls.cn' in url:
                    url = url.replace('www.tfls.cn', 'tfls.tj.edu.cn')
                page['file_urls'].append(url)
            yield page
    
    def parse_xsc(self, res):
        items = res.json()['data']['list']

        for item in items:
            page = PageItem()
            page['title'] = item['title']
            page['author'] = item['createUser']
            page['date'] = f"{item['publishTime'][0:10]}T00:00:00+08:00"
            page['content'] = item['content']
            page['slug'] = md5(page['title'].encode()).hexdigest()
            page['path'] = 'admission'
            page['description'] = item['brief']
            page['categories'] = ['招生信息']
            page['tags'] = ['小升初']
            yield page