# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from pathlib import Path
import json
import logging
from io import BytesIO

from markdownify import MarkdownConverter
from contextlib import suppress
from twisted.internet import defer

from itemadapter import ItemAdapter
from scrapy.pipelines.files import FileException
from scrapy.pipelines.images import ImagesPipeline
from scrapy.utils.request import referer_str

logger = logging.getLogger(__name__)

class _ImageBlockConverter(MarkdownConverter):
    def convert_img(self, el, text, convert_as_inline):
        alt = el.attrs.get('alt', None) or ''
        src = el.attrs.get('src', None) or ''
        width = el.attrs.get('width', None) or ''
        height = el.attrs.get('height', None) or ''
        title = el.attrs.get('title', None) or ''
        title_part = ' "%s"' % title.replace('"', r'\"') if title else ''
        if (convert_as_inline and el.parent.name not in self.options['keep_inline_images_in']):
            return alt

        return f'''
<img
    src="{src}"
    style="display:block;margin-left:auto;margin-right:auto;"
    decoding="async"
    fetchpriority="auto"
    loading="lazy"'''+(f'''
    alt="{alt}"''' if alt else '')+(f'''
    title="{title}"''' if title else '')+(f'''
    height="{height}"''' if height else '')+(f'''
    width="{width}"''' if width else '')+'\n/>'

def _md(html, **options):
    return _ImageBlockConverter(**options).convert(html)

class RewriteImageURLPipeline:
    def process_item(self, item, spider):
        content = item['content']
        for img in item['images']:
            content = content.replace(img['url']+"\"", f"https://cdn.tfls.online/mirror/{img['path']}\" width='{img['size'][0]}' height='{img['size'][1]}'")
            content = content.replace(img['url']+"\'", f"https://cdn.tfls.online/mirror/{img['path']}\" width='{img['size'][0]}' height='{img['size'][1]}'")
        item['content'] = content
        return item

class ConvertToMarkdownPipeline:
    def process_item(self, item, spider):
        item['content'] = _md(item['content'], heading_style="ATX") 
        return item

class ExportMarkdownPipeline:
    def process_item(self, item, spider):
        dir = f"./.scrapy/output/{item['path']}"
        Path(dir).mkdir(parents=True, exist_ok=True)
        self.file = open(f"{dir}/{item['slug']}.md", "w")
        md_frontmatter = { 'toc': True,
            'date': item.get('date', None),
            'title': item.get('title', None),
            'params': {
                'author': item.get('author', None)
            } if item.get('author', False) else None,
            'description': item.get('description', None),
            'summary': item.get('description', None),
            'isCJKLanguage': True,
            'aliases': [item.get('url', '').replace('http://work.tfls.tj.edu.cn', '')] if item.get('url', False) else None,
            'slug': item.get('slug', None),
            'categories': item.get('categories', None),
            'tags': item.get('tags', None),
            'weight': item.get('weight', None),
            'contributors': [] # doks compatibility
        }
        for key, value in list(md_frontmatter.items()):
            if value is None:
                del md_frontmatter[key]
        self.file.write(json.dumps(md_frontmatter, indent=4, sort_keys=True) + '\n' + item['content'])
        self.file.close()
        return item

class ImagesWithMetaPipeline(ImagesPipeline):  
    def item_completed(self, results, item, info):
        with suppress(KeyError):
            ItemAdapter(item)[self.images_result_field] = [x for ok, x in results if ok]
        return item

    def media_downloaded(self, response, request, info, *, item=None):
        referer = referer_str(request)

        if response.status != 200:
            logger.warning(
                "File (code: %(status)s): Error downloading file from "
                "%(request)s referred in <%(referer)s>",
                {"status": response.status, "request": request, "referer": referer},
                extra={"spider": info.spider},
            )
            raise FileException("download-error")

        if not response.body:
            logger.warning(
                "File (empty-content): Empty file from %(request)s referred "
                "in <%(referer)s>: no-content",
                {"request": request, "referer": referer},
                extra={"spider": info.spider},
            )
            raise FileException("empty-content")

        status = "cached" if "cached" in response.flags else "downloaded"
        logger.debug(
            "File (%(status)s): Downloaded file from %(request)s referred in "
            "<%(referer)s>",
            {"status": status, "request": request, "referer": referer},
            extra={"spider": info.spider},
        )
        self.inc_stats(info.spider, status)

        try:
            path = self.file_path(request, response=response, info=info, item=item)
            checksum = self.file_downloaded(response, request, info, item=item)
        except FileException as exc:
            logger.warning(
                "File (error): Error processing file from %(request)s "
                "referred in <%(referer)s>: %(errormsg)s",
                {"request": request, "referer": referer, "errormsg": str(exc)},
                extra={"spider": info.spider},
                exc_info=True,
            )
            raise
        except Exception as exc:
            logger.error(
                "File (unknown-error): Error processing file from %(request)s "
                "referred in <%(referer)s>",
                {"request": request, "referer": referer},
                exc_info=True,
                extra={"spider": info.spider},
            )
            raise FileException(str(exc))

        image = self._Image.open(BytesIO(response.body))

        return {
            "url": request.url,
            "path": path,
            "checksum": checksum,
            "status": status,
            "size": image.size
        }

    def media_to_download(self, request, info, *, item=None):
        def _onsuccess(result):
            if not result:
                return  # returning None force download

            last_modified = result.get("last_modified", None)
            if not last_modified:
                return  # returning None force download

            age_seconds = time.time() - last_modified
            age_days = age_seconds / 60 / 60 / 24
            if age_days > self.expires:
                return  # returning None force download

            referer = referer_str(request)
            logger.debug(
                "File (uptodate): Downloaded %(medianame)s from %(request)s "
                "referred in <%(referer)s>",
                {"medianame": self.MEDIA_NAME, "request": request, "referer": referer},
                extra={"spider": info.spider},
            )
            self.inc_stats(info.spider, "uptodate")

            checksum = result.get("checksum", None)

            image = self._Image.open(BytesIO(response.body))

            return {
                "url": request.url,
                "path": path,
                "checksum": checksum,
                "status": status,
                "size": image.size
            }

        path = self.file_path(request, info=info, item=item)
        dfd = defer.maybeDeferred(self.store.stat_file, path, info)
        dfd.addCallback(_onsuccess)
        dfd.addErrback(lambda _: None)
        dfd.addErrback(
            lambda f: logger.error(
                self.__class__.__name__ + ".store.stat_file",
                exc_info=failure_to_exc_info(f),
                extra={"spider": info.spider},
            )
        )
        return dfd