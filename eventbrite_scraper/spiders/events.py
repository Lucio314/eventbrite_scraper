import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service  # Import pour Selenium 4
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scrapy import signals
from pydispatch import dispatcher
import time


class EventSpider(scrapy.Spider):
    name = "events"
    allowed_domains = ["eventbrite.com"]

    categories_dict = {
        "business": 22,
        "food-and-drink": 1,
        "health": 10,
        "music": 2,
        "auto-boat-and-air": 1,
        "charity-and-causes": 1,
        "community": 2,
        "family-and-education": 2,
        "fashion": 1,
        "film-and-media": 1,
        "hobbies": 1,
        "home-and-lifestyle": 1,
        "performing-and-visual-arts": 6,
        "government": 1,
        "spirituality": 2,
        "school-activities": 1,
        "science-and-tech": 15,
        "holidays": 2,
        "sports-and-fitness": 5,
        "travel-and-outdoor": 3,
        "other": 2,
    }

    def __init__(self, *args, **kwargs):
        super(EventSpider, self).__init__(*args, **kwargs)
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Utilisation du Service pour spécifier le chemin de chromedriver
        self.driver = webdriver.Chrome(
            service=Service("C:/chromedriver-win64/chromedriver.exe"),
            options=chrome_options,
        )
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    def spider_closed(self, spider):
        self.driver.quit()

    def start_requests(self):
        base_url = (
            "https://www.eventbrite.com/d/switzerland/{category}--events/?page={page}"
        )
        for category, num_pages in self.categories_dict.items():
            for page in range(1, num_pages + 1):
                url = base_url.format(category=category, page=page)
                yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        category_slug = response.url.split("/")[5].split("--")[0]
        events = response.css("div.event-card__horizontal")
        for event in events:
            title = event.css("h3::text").get()
            date = event.css("p.event-card__clamp-line--one::text").get()
            location_elements = event.css(
                "p.event-card__clamp-line--one::text"
            ).getall()
            location = (
                location_elements[1] if len(location_elements) > 1 else "Not Available"
            )
            image = event.css("img::attr(src)").get()
            price = event.xpath(
                './/div[contains(@class, "DiscoverHorizontalEventCard-module__priceWrapper___3rOUY")]/p[contains(@class, "Typography_body-md-bold__487rx")]/text()'
            ).get()
            event_link = event.css("a.event-card-link::attr(href)").get()

            event_data = {
                "title": title,
                "date": date.strip() if date else None,
                "location": location.strip() if location else "Not Available",
                "image": image,
                "category": category_slug,
                "price": price if price else "Not Available",
                "event_link": event_link,
                "description": "",
            }

            if event_link:
                yield scrapy.Request(
                    url=event_link,
                    callback=self.parse_event,
                    meta={"event_data": event_data},
                )

    def parse_event(self, response):
        event_data = response.meta["event_data"]

        # Naviguer avec Selenium sur la page pour récupérer la description dynamique
        self.driver.get(response.url)
        time.sleep(3)  # Pause pour charger le contenu JavaScript

        try:
            WebDriverWait(self.driver, 10).until(
                EC.visibility_of_element_located(
                    (By.CSS_SELECTOR, "div.event-description__content")
                )
            )
            description_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "div.event-description__content *"
            )
            description = " ".join(
                [
                    element.text.strip()
                    for element in description_elements
                    if element.text.strip()
                ]
            )
            event_data["description"] = (
                (description[:255] + "...") if len(description) > 255 else description
            )
        except Exception:
            event_data["description"] = "Not Available"

        yield event_data
