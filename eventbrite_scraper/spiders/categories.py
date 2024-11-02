import scrapy
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from scrapy import signals
from pydispatch import dispatcher
import time

class EventbriteSpider(scrapy.Spider):
    name = 'categories'
    start_urls = ['https://www.eventbrite.com/d/switzerland/all-events/']

    def __init__(self, *args, **kwargs):
        super(EventbriteSpider, self).__init__(*args, **kwargs)
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        # Initialisation de Selenium avec le chemin du chromedriver
        self.driver = webdriver.Chrome(service=Service("C:/chromedriver-win64/chromedriver.exe"), options=chrome_options)
        dispatcher.connect(self.spider_closed, signals.spider_closed)

        # Dictionnaires pour stocker les catégories et le nombre de pages
        self.categories_dict = {}
        self.pages_dict = {}

    def spider_closed(self, spider):
        # Fermer le navigateur Selenium à la fin
        self.driver.quit()

    def parse(self, response):
        # Ouvrir la page de démarrage avec Selenium
        self.driver.get(response.url)
        time.sleep(3)  # Attendre le chargement initial

        # Cliquer sur le bouton "Voir plus" pour afficher toutes les catégories
        try:
            view_more_button = self.driver.find_element(By.XPATH, '//button[@data-testid="read-more-toggle"]')
            view_more_button.click()
            time.sleep(2)  # Attendre que les catégories supplémentaires se chargent
        except Exception:
            self.logger.info("Le bouton 'Voir plus' n'a pas été trouvé ou n'a pas pu être cliqué.")

        # Récupérer toutes les catégories et leurs liens
        category_elements = self.driver.find_elements(By.CSS_SELECTOR, 'a[data-testid^="category-filter-"]')
        
        for category in category_elements:
            name = category.find_element(By.CSS_SELECTOR, 'span').text
            link = category.get_attribute('href')
            self.categories_dict[name] = response.urljoin(link)

        # Passer à la prochaine étape : collecte du nombre de pages par catégorie
        for name, link in self.categories_dict.items():
            yield scrapy.Request(url=link, callback=self.parse_category, meta={'category_name': name})

    def parse_category(self, response):
        category_name = response.meta['category_name']
        
        # Rechercher l'élément de pagination pour obtenir le nombre de pages
        pagination = response.css('li[data-testid="pagination-parent"] span[data-testid="pagination-string"]::text').get()
        
        # Si la pagination est présente, extraire le nombre de pages
        if pagination:
            total_pages = int(pagination.split("of")[-2:-1].strip())
        else:
            total_pages = 1  # Si aucune pagination n'est trouvée, on suppose une seule page

        # Enregistrer le nombre de pages dans le dictionnaire
        self.pages_dict[category_name] = total_pages

        # Afficher le résultat une fois toutes les catégories traitées
        if len(self.pages_dict) == len(self.categories_dict):
            self.logger.info("Catégories et liens : %s", self.categories_dict)
            self.logger.info("Nombre de pages par catégorie : %s", self.pages_dict)
