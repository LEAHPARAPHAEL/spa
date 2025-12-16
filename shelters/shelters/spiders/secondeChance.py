import scrapy
from urllib.parse import urljoin
import re
import html
import os
import json


def load_french_dictionary(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            vocab_set = {line.strip().lower() for line in f if line.strip()}
            
        return vocab_set
        
    except:
        raise(Exception("Problem loading the dictionary."))



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

    # Breeds mapping to try to map the dog's breed with one from the dataset
    breeds = json.load(open("data/breeds_mapping.json", "r"))

    # Part of the mapping concerning this site
    seconde_chance_breeds = breeds["seconde chance"]

    french_dictionary = load_french_dictionary("data/french_dictionary.txt")


    def parse(self, response):
        # Extracts each dog card
        for href in response.xpath("//div[contains(@class, 'p-6')]/div//a[contains(@href, '/animal/chien-')]/@href").getall():
            yield response.follow(href, callback=self.parse_dog)

        # Finds the next page button
        next_page = response.xpath("//a[@rel='next']/@href").get()
        if next_page:
            yield response.follow(next_page, callback=self.parse)

    def parse_dog(self, response):

        image_urls = [
            response.urljoin(u)
            for u in response.xpath("//img[contains(@src, '/uploads/')]/@src").getall()
        ]

        # Gets and cleans the name of the dog
        name = self.clean_dog_name(response.xpath("//h1/text()").get() or None, self.french_dictionary)

        # Gets and cleans the species of the dog ("Chien")
        species = self.remove_colons(response.xpath("//p/strong[text()='Espèce']/following-sibling::text()").get() or None)

        # Gets and cleans the breed of the dog
        breed = self.remove_colons(response.xpath("//p/strong[text()='Type']/following-sibling::text()").get().lower() or None)

        # Tries to match this breed against one from the dataset
        if breed:
            matched_breed = self.seconde_chance_breeds.get(breed.lower(), {}).get("matched_breed", None)
        else:
            matched_breed = None

        # Gets, cleans and translates the sex of the dog
        sex = self.remove_colons(response.xpath("//p/strong[text()='Sexe']/following-sibling::text()").get() or None)
        sex = self.sex_to_english(sex)

        # Gets the colors of the dogs
        colors = self.remove_colons(response.xpath("//p/strong[text()='Couleur']/following-sibling::text()").get() or None)

        # Gets the age of the dog, and creates two fields, one for the text version ("4 years") and one as a float 4.0
        # Both can be useful depending on the setting.
        age_text = self.remove_colons(response.xpath("//p/strong[text()='Âge']/following-sibling::text()").get() or None)
        if age_text:
            age_text = self.age_to_english(age_text)
            age = self.age_text_to_float(age_text)
        else:
            age = None

        # By default, nothing is specified on a dog's page about its incompatibilities.
        # But, if the dog is incompatible with children, cats or other dogs, the only thing I have found in common
        # in all html files is the pictogram of said incompatibility. 
        accepts_children = False if response.xpath("//ul[@class='particularities']/li/span[@class='icon-picto-enfant']").get() else True

        accepts_cats = False if response.xpath("//ul[@class='particularities']/li/span[@class='icon-picto-chat']").get() else True  

        accepts_dogs = False if response.xpath("//ul[@class='particularities']/li/span[@class='icon-picto-chien']").get() else True                    
                    
        # Gets the informations about the establishment
        establishment = self.clean(response.xpath("//p[@class='my-6 font-bold text-orange-sc'][1]/a/u/text()").get() or None)

        establishment_url = self.clean(response.xpath("//p[@class='my-6 font-bold text-orange-sc'][1]/a/@href").get() or None)


        # Builds the record
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
    
    
    def clean_dog_name(self, raw_text, dictionary_set):

        if not raw_text or not isinstance(raw_text, str):
            return None

        # Avoids characters like html rsquo
        text = html.unescape(raw_text)

        # Regex pattern
        pattern = r"^([^\W\d_]|[\s\-'’])+"
        match = re.match(pattern, text)
        
        if not match:
            return None
            
        # Takes the first part before the occurrence of the first non alphabetical character
        cleaned_name = match.group(0).strip()

        # Removes weird patterns that are specific to the two shelters, especially SPA
        pattern = r"(\-|\s*\(.*|\s*&.*|\s+\bQCN\b.*|\s+\bVAA\b.*|\s+\bCHAO\b.*|\s+\bHAA\b.*|\s+\w*\d{5}.*)"
        
        # Replaces the matching pattern with an empty string
        cleaned_name = re.sub(pattern, "", cleaned_name, flags=re.IGNORECASE)
        
        tokens = cleaned_name.split()
        
        if not tokens:
            return None

        # Checks if some french word artefacts are still present in the name
        is_french_word = []
        for token in tokens:

            token_clean = token.lower().strip("-'’")
            
            # Check if in dictionary
            is_french_word.append(token_clean in dictionary_set)

        # If all the words are potentially french words, we have to output everything, because
        # we cannot be sure.
        if all(is_french_word):
            return cleaned_name.title()
        else:
            final_tokens = []
            for word, is_french in zip(tokens, is_french_word):
                if not is_french:
                    final_tokens.append(word)
                    
            return " ".join(final_tokens).title()


    def age_to_category(self, age_float):
        if age_float < 3.0: 
            return "junior"
        elif 3.0 <= age_float < 10.0:
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

