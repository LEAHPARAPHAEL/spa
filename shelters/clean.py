import json
import re
import html

def clean_dog_name(name):
    name = html.unescape(name)
    pattern = r"(\s*\(.*|\s*&.*|\s+\bQCN\b.*|\s+\bVAA\b.*|\s+\w*\d{5}.*)"
    
    # Replace the matching pattern with an empty string
    cleaned_name = re.sub(pattern, "", name, flags=re.IGNORECASE)
    return cleaned_name.strip()



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



def clean_seconde_chance_json(input_file, output_file):
    with open(input_file, 'r', encoding='utf-8') as infile, \
        open(output_file, 'w', encoding='utf-8') as outfile:
        
        for line in infile:
            if line.strip(): # Skip empty lines
                data = json.loads(line)
                # Remove the key if it exists
                #data.pop('description', None)
                breed = data.get("breed", None)
                if breed:
                    matched_breed = breeds.get(breed.lower(), {}).get("matched_breed", None)
                else:
                    matched_breed = None
                data["matched_breed"] = matched_breed

                for k in data.keys():
                    if data[k] == "":
                        data[k] = None
                
                name = data["name"]
                name = clean_dog_name(name)
                data["name"] = name

                sex = data["sex"]
                sex = re.sub("Femelle", "Female", sex)
                sex = re.sub("Mâle", "Male", sex)
                data["sex"] = sex
                

                data = reorder_dict(data)
                # Write back to file as one line per object
                outfile.write(json.dumps(data, ensure_ascii=False) + '\n')

    print("Cleaned seconde chance.")


if __name__ == "__main__":
    # Replace 'dogs.json' with your filename
    input_file = 'data/seconde_chance.jsonl'
    output_file = 'data/seconde_chance_clean.jsonl'

    breeds = json.load(open("data/breeds_mapping.json", "r"))["seconde chance"]

    clean_seconde_chance_json(input_file, output_file)