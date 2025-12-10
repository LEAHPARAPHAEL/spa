import scrapy
from urllib.parse import urljoin
import re
import html
import os
import json

class SecondeChanceDogsSpider(scrapy.Spider):
    name = "secondeChance"
    allowed_domains = ["secondechance.org"]
    start_urls = ["https://www.secondechance.org/animal/recherche?department=&species=1"]

    custom_settings = {
        "ROBOTSTXT_OBEY": True,
        "AUTOTHROTTLE_ENABLED": True,
        "AUTOTHROTTLE_START_DELAY": 1.0,
        "AUTOTHROTTLE_MAX_DELAY": 10.0,
        "CONCURRENT_REQUESTS": 1,
        "DOWNLOAD_DELAY": 1.0,
        "FEED_EXPORT_ENCODING": "utf-8",
    }

    breeds = json.load(open("data/breeds_mapping.json", "r"))

    seconde_chance_breeds = breeds["seconde chance"]


    def parse(self, response):
        # Extract each dog card
        for href in response.xpath("//div[contains(@class, 'p-6')]/div//a[contains(@href, '/animal/chien-')]/@href").getall():
            yield response.follow(href, callback=self.parse_dog)

        # Handle pagination (next page button)
        next_page = response.xpath("//a[@rel='next']/@href").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def clean(self, x):
        return x.strip() if x else None

    def remove_colons(self, x):
        return x.replace(":", "").strip() if x else ""

    def decode(self, x):
        if not x:
            return ""
        x = html.unescape(x) 
        x = re.sub(r"\s+", " ", x)  
        return x.strip()

    def age_text_to_float(self, age_text):
        years = 0
        months = 0

        # Match years
        match_years = re.search(r'(\d+)\s*years?', age_text)
        if match_years:
            years = int(match_years.group(1))

        # Match months
        match_months = re.search(r'(\d+)\s*months', age_text)
        if match_months:
            months = int(match_months.group(1))

        age_float = years + months / 12
        return round(age_float, 2)
    
    def clean_dog_name(self, name):
        name = html.unescape(name)
        pattern = r"(\s*\(.*|\s*&.*|\s+\bQCN\b.*|\s+\bVAA\b.*|\s+\w*\d{5}.*)"
        
        # Replace the matching pattern with an empty string
        cleaned_name = re.sub(pattern, "", name, flags=re.IGNORECASE)
        return cleaned_name.strip()

    def age_to_category(self, age_float):
        if age_float < 1.0: 
            return "junior"
        elif 1.0 <= age_float < 7.0:
            return "adult"
        else:
            return "senior"
        
    def age_to_english(self, age_text):
        age_text = re.sub("an", "year", age_text)
        age_text = re.sub("mois", "months", age_text)

        return age_text
    
    def sex_to_english(self, sex):
        if not sex:
            return None
        sex = re.sub("Femelle", "Female", sex)
        sex = re.sub("Mâle", "Male", sex)

        return sex

    def parse_dog(self, response):

        image_urls = [
            response.urljoin(u)
            for u in response.xpath("//img[contains(@src, '/uploads/')]/@src").getall()
        ]

        name = self.clean(response.xpath("//h1/text()").get() or None)
        if name:
            name = self.clean_dog_name(name)

        species = self.remove_colons(response.xpath("//p/strong[text()='Espèce']/following-sibling::text()").get() or None)

        breed = self.remove_colons(response.xpath("//p/strong[text()='Type']/following-sibling::text()").get().lower() or None)

        sex = self.remove_colons(response.xpath("//p/strong[text()='Sexe']/following-sibling::text()").get() or None)
        sex = self.sex_to_english(sex)

        colors = self.remove_colons(response.xpath("//p/strong[text()='Couleur']/following-sibling::text()").get() or None)

        age_text = self.remove_colons(response.xpath("//p/strong[text()='Âge']/following-sibling::text()").get() or None)
        if age_text:
            age_text = self.age_to_english(age_text)
            age = self.age_text_to_float(age_text)
        else:
            age = None

        accepts_children = False if response.xpath("//ul[@class='particularities']/li/span[@class='icon-picto-enfant']").get() else True

        accepts_cats = False if response.xpath("//ul[@class='particularities']/li/span[@class='icon-picto-chat']").get() else True  

        accepts_dogs = False if response.xpath("//ul[@class='particularities']/li/span[@class='icon-picto-chien']").get() else True                    
                    
        establishment = self.clean(response.xpath("//p[@class='my-6 font-bold text-orange-sc'][1]/a/u/text()").get() or None)

        establishment_url = self.clean(response.xpath("//p[@class='my-6 font-bold text-orange-sc'][1]/a/@href").get() or None)

        #description_nodes = response.xpath("//p[@class='font-bold']/following-sibling::p[not(strong)]//text()").getall()
        #description = self.decode(" ".join(description_nodes))

        # The commented part below was useful to extract all the breeds in the database to construct a mapping with the breeds dataset.
        '''
        if breed:


            os.makedirs("data", exist_ok=True)
            filepath = "data/breeds.txt"
            
            # Read existing breeds (if file exists)
            if os.path.exists(filepath):
                mode = 'a'
                with open(filepath, "r", encoding="utf-8") as f:
                    existing = {line.strip().lower() for line in f if line.strip()}
            else:
                mode = 'w'
                existing = set()
            
            # Add only if new
            if breed.lower() not in existing:
                with open(filepath, mode, encoding="utf-8") as f:
                    f.write(breed.lower().strip() + "\n")
                self.logger.info(f"Added new breed: {breed}")
        '''
            
        if breed:
            matched_breed =  self.seconde_chance_breeds.get(breed.lower(), {}).get("matched_breed", None)
        else:
            matched_breed = None
        


        yield {
            "source": "Seconde Chance",
            "url": response.url,
            "name":name,
            "species": species,
            "sex": sex,
            "age text": age_text,
            "age" : age,
            "category" : self.age_to_category(age),
            "breed": breed,
            "matched_breed" : matched_breed,
            "colors": colors,
            "accepts_dogs" : accepts_dogs,
            "accepts_cats" : accepts_cats,
            "accepts_children" : accepts_children,
            #"description": description,
            "establishment" : establishment,
            "establishment_url" : establishment_url,
            "image_urls": image_urls
        }



