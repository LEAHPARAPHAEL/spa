import json
import re
import html


def load_french_dictionary(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            vocab_set = {line.strip().lower() for line in f if line.strip()}
            
        return vocab_set
        
    except:
        raise(Exception("Problem loading the dictionary."))


def clean_dog_name(raw_text, dictionary_set):
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



def reorder_dict(dog_data):
    # Define the exact order you want
    desired_order = [
        "source",
        "url",
        "name",
        "species",
        "sex",
        "age_text",
        "age",
        "category",
        "breed",
        "matched_breed",
        "colors",
        "accepts_dogs",
        "accepts_cats",
        "accepts_children",
        "establishment",
        "establishment_url",
        "image_urls"
    ]
    
    ordered_dict = {}
    
    for key in desired_order:
        if key in dog_data:
            ordered_dict[key] = dog_data[key]
    return ordered_dict

def age_to_category(age_float):
        if age_float < 3.0: 
            return "junior"
        elif 3.0 <= age_float < 10.0:
            return "adult"
        else:
            return "senior"

def clean_json(input_file, output_file, french_dictionary):
    with open(input_file, 'r', encoding='utf-8') as infile, \
        open(output_file, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            if line.strip(): 
                data = json.loads(line)

                '''
                breed = data.get("breed", None)
                if breed:
                    matched_breed = breeds.get(breed.lower(), {}).get("matched_breed", None)
                else:
                    matched_breed = None
                data["matched_breed"] = matched_breed
                '''

                name = data["name"]
                name = clean_dog_name(name, french_dictionary)
                data["name"] = name


                data = reorder_dict(data)
                outfile.write(json.dumps(data, ensure_ascii=False) + '\n')



if __name__ == "__main__":
    # Replace 'dogs.json' with your filename
    seconde_chance = 'data/seconde_chance.jsonl'
    seconde_chance_clean = 'data/seconde_chance_clean.jsonl'

    spa = 'data/spa.jsonl'
    spa_clean = 'data/spa_clean.jsonl'

    breeds = json.load(open("data/breeds_mapping.json", "r"))["seconde chance"]

    french_dictionary = load_french_dictionary("data/french_dictionary.txt")

    clean_json(seconde_chance, seconde_chance_clean, french_dictionary)
    clean_json(spa, spa_clean, french_dictionary)