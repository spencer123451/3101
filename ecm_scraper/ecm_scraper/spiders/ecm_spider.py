import scrapy
import os

class ECMScraperSpider(scrapy.Spider):
    name = "ecm_spider"

    def start_requests(self):
        # Use the relative path to the file
        file_path = os.path.join('data', 'links_domain=eurostatwbsg_lang=en.nt')
        
        # Read URLs from file
        with open(file_path, 'r') as file:
            lines = file.readlines()
        
        urls = set()
        for line in lines:
            parts = line.split(' ')
            if len(parts) > 2:
                urls.add(parts[0].strip('<>'))
                urls.add(parts[2].strip('<>'))

        # Limit the number of URLs to 100
        for i, url in enumerate(urls):
            if i >= 100:
                break
            yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        """
        Parses the response from each URL request to extract relevant data from the webpage.

        Input: response : scrapy.http.Response

        Output:
        dict
            A dictionary containing the extracted data from the webpage, which includes:
            - url (str): The URL of the webpage being scraped.
            - title (str or None): The text content of the <title> tag in the HTML. Returns None if not found.
            - headings (list of str): A list of all <h1> heading texts found on the page. Returns an empty list if none are found.
            - paragraphs (list of str): A list of all paragraph texts (<p> tags) found on the page. Returns an empty list if none are found.
            - headers (dict): A dictionary of HTTP headers received in the response.

        Description:
        ------------
        This method is a callback function that Scrapy calls automatically whenever a response is received from a URL request.
        It processes the HTML content of the page to extract specific pieces of information such as the page title, headings,
        paragraphs, and HTTP headers. The extracted data is then yielded as a dictionary, which Scrapy collects and processes
        further according to the specified output format (e.g., JSON, CSV).

        Example:
        --------
        An example of the yielded output might look like:
    
        """
        title = response.xpath('//title/text()').get()
        headings = response.xpath('//h1/text()').getall()
        paragraphs = response.xpath('//p/text()').getall()

        # Extracting headers and other relevant information
        headers = response.headers.to_unicode_dict()  # Converts headers to a readable dictionary

        # Yielding all extracted data
        yield {
            'url': response.url,
            'title': title,
            'headings': headings,
            'paragraphs': paragraphs,
            'headers': headers
        }
        
