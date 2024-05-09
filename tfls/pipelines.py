# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html

from pathlib import Path
import json

import markdownify 

class RewriteImageURLPipeline:
    def process_item(self, item, spider):
        content = item['content']
        for img in item['files']:
            content = content.replace(img['url'], f"https://cdn.tfls.online/mirror/{img['path']}")
        item['content'] = content
        return item

class ConvertToMarkdownPipeline:
    def process_item(self, item, spider):
        item['content'] = markdownify.markdownify(item['content'], heading_style="ATX") 
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
            'aliases': [item.get('url', '').replace('http://tfls.tj.edu.cn', '')] if item.get('url', False) else None,
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