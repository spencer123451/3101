import scrapy
from scrapy.exceptions import CloseSpider
from ..items import WebItem
import re

class WebspiderSpider(scrapy.Spider):
    name = "webspider"
    allowed_domains = ["dbpedia.org"]
    start_urls = ["http://dbpedia.org/"]

    def start_requests(self):
        # Clean the URLs from the file
        cleaned_urls = self.clean_urls('../../New1.txt')
        
        if not cleaned_urls:
            self.logger.error("No valid URLs found. Exiting spider.")
            raise CloseSpider('No URLs found')
        
        for url in cleaned_urls:
            self.logger.info(f'Scraping URL: {url}')
            yield scrapy.Request(url=url, callback=self.parse_book_page, errback=self.handle_error)

    def clean_urls(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as file:
                raw_data = file.read()

            # Extract URLs from RDF triples using regex
            urls = re.findall(r'<(http://dbpedia\.org/resource/[^>]*)>', raw_data)

            # Deduplicate URLs
            unique_urls = list(set(urls))

            self.logger.info(f'Cleaned {len(urls)} raw URLs to {len(unique_urls)} unique DBpedia URLs.')
            return unique_urls
        except FileNotFoundError as e:
            self.logger.error(f"File not found: {e}")
            return []
        except UnicodeDecodeError as e:
            self.logger.error(f"Encoding error: {e}")
            return []
        except Exception as e:
            self.logger.error(f"Error in clean_urls: {e}")
            return []

    def parse_book_page(self, response):
        if response.status == 404:
            self.logger.info(f"Page not found: {response.url}")
            return
        
        self.logger.info(f'Parsing URL: {response.url}')
        book_item = WebItem()
        
        book_item['url'] = response.url
        
        # Wikipedia link extraction
        wikipedia_link = response.css('td.col-10 span.literal a[href*="wikipedia.org"]::attr(href)').get()
        if wikipedia_link:
            book_item['wikipedia_link'] = wikipedia_link

        # Photo URL extraction
        photo_url = response.css('.container-xl .row .table-responsive .table.table-hover.table-sm.table-light .even .col-10.text-break ul li .literal a.uri::attr(href)').get()
        if photo_url:
            book_item['photo_url'] = photo_url

        # Lead text extraction
        lead_text = response.css('p.lead::text').get()
        if lead_text:
            book_item['lead_text'] = lead_text.strip()

        # Yield the populated book_item
        yield book_item

    def handle_error(self, failure):
        self.logger.error(f"Request failed: {failure}")
