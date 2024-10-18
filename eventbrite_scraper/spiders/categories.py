import scrapy

class EventbriteSpider(scrapy.Spider):
    name = 'eventbrite'
    start_urls = ['https://www.eventbrite.com/d/switzerland/all-events/']

    def parse(self, response):
        # Sélecteur CSS plus général
        categories = response.css('a[data-testid^="category-filter-"]')

        for category in categories:
            yield {
                'name': category.css('span::text').get(),
                'link': response.urljoin(category.attrib['href']),
            }
