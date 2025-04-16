# TFLS Scraper

![last commit](https://img.shields.io/gitea/last-commit/TFLSOnline/tfls-scraper?gitea_url=https://code.dragoncloud.win)![latest release](https://img.shields.io/gitea/v/release/TFLSOnline/tfls-scraper?gitea_url=https://code.dragoncloud.win)


## Introduction

The project crawls [http://tfls.tj.edu.cn](http://tfls.tj.edu.cn) and mirrors it to [https://tfls.online](https://tfls.online). 

The official TFLS ([http://tfls.tj.edu.cn](http://tfls.tj.edu.cn)) is very out-of-date and unstable. This project aims to provide a modern mirror with all contents re-built using modern frontend stack.

This repo is available both at [https://code.dragoncloud.win/TFLSOnline/tfls-scraper](https://code.dragoncloud.win/TFLSOnline/tfls-scraper) and [GitHub](https://github.com/holgerhuo/tfls-scraper)

## Usage

```
pip3 install -r requirements.txt
scrapy crawl tfls
```

## To-dos

- [ ] Automation with GitHub Actions and Docker
- [ ] Scrape articles from WeChat

## License

GNU General Public License v3.0

© Holger Huo