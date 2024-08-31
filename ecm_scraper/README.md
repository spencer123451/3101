# Running of scrapy

## Start new scrapy (skip)
scrapy startproject ecm_scraper  

## make sure at correct directory
cd ecm_scraper        

## run ecm_scrapy.py file
scrapy crawl ecm_spider -o output.json

# if ran correctly, a json file should appear