import scrapy


class EventSpider(scrapy.Spider):
    name = "events"
    allowed_domains = ["eventbrite.com"]
    # Dictionnaire des catégories avec le nombre de pages
    categories_dict = {
        # "business": 22,
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

    def start_requests(self):
        base_url = (
            "https://www.eventbrite.com/d/switzerland/{category}--events/?page={page}"
        )
        # Pour chaque catégorie, on génère l'URL et fait une requête Scrapy
        for category, num_pages in self.categories_dict.items():
            for page in range(
                1, num_pages + 1
            ):  # Parcourir jusqu'au nombre de pages spécifié
                url = base_url.format(category=category, page=page)
                yield scrapy.Request(url=url, callback=self.parse)

    def parse(self, response):
        category_slug = response.url.split("/")[5].split("--")[
            0
        ]  # Extraire la catégorie depuis l'URL
        events = response.css("div.event-card__horizontal")
        for event in events:
            title = event.css("h3::text").get()
            date = event.css("p.event-card__clamp-line--one::text").get()
            location_elements = event.css(
                "p.event-card__clamp-line--one::text"
            ).getall()
            location = location_elements[1] if len(location_elements) > 1 else None
            image = event.css("img::attr(src)").get()
            price = event.xpath(
                './/div[contains(@class, "DiscoverHorizontalEventCard-module__priceWrapper___3rOUY")]/p[contains(@class, "Typography_body-md-bold__487rx")]/text()'
            ).get()
            event_link = event.css("a.event-card-link::attr(href)").get()
            yield {
                "title": title,
                "date": date.strip() if date else None,
                "location": location.strip() if location else "Not Available",
                "image": image,
                "category": category_slug,
                "price": price if price else "Not Available",
                "description": "",
                "event_link": event_link,
            }
            if event_link:
                yield response.follow(
                    event_link,
                    self.parse_event,
                    meta={
                        "event_data": {
                            "title": title,
                            "location": (
                                location.strip() if location else "Not Available"
                            ),
                            "date": date.strip() if date else None,
                            "image": image,
                            "category": category_slug,
                            "price": price if price else "Not Available",
                            "event_link": event_link,
                        }
                    },
                )

    def parse_event(self, response):
        event_data = response.meta["event_data"]
        # Récupérer le texte de la description avec tout le contenu structuré
        description = response.css("div.event-description__content *::text").getall()
        # Nettoyer et formater la description
        description = " ".join([text.strip() for text in description if text.strip()])
        event_data["description"] = description if description else None
        yield event_data
