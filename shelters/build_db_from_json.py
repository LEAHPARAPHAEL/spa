import sqlite3, json, glob
import os
import csv

conn = sqlite3.connect("data/shelters.db")
cur = conn.cursor()

# Recreate table if needed
cur.execute("""
CREATE TABLE IF NOT EXISTS dogs (
    id INTEGER PRIMARY KEY,
    source TEXT,
    name TEXT,
    url TEXT UNIQUE,
    species TEXT,
    sex TEXT,
    age_text TEXT,
    age REAL,
    category TEXT,
    breed TEXT,
    matched_breed TEXT,
    colors TEXT,
    accepts_dogs BOOL,
    accepts_cats BOOL,
    accepts_children BOOL,
    establishment TEXT, 
    establishment_url TEXT
)
""")

cur.execute("""
CREATE TABLE IF NOT EXISTS images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dog_id INTEGER,
    image_url TEXT,
    FOREIGN KEY (dog_id) REFERENCES dogs (id) ON DELETE CASCADE
)
""")

for file in glob.glob("data/seconde_chance.jsonl"):
    print("Loading", file)
    with open(file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                item = json.loads(line)
                cur.execute("""
                INSERT OR IGNORE INTO dogs
                (source, name, url, species, sex, age_text, age, category, breed, matched_breed, colors, accepts_dogs, accepts_cats, accepts_children, establishment, establishment_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "Seconde chance",
                    item.get("name"),
                    item.get("url"),
                    item.get("species"),
                    item.get("sex"),
                    item.get("age_text"),
                    item.get("age"),
                    item.get("category"),
                    item.get("breed"),
                    item.get("matched_breed"),
                    item.get("colors"),
                    item.get("accepts_dogs"),
                    item.get("accepts_cats"),
                    item.get("accepts_children"),
                    item.get("establishment"),
                    item.get("establishment_url")
                ))

                current_dog_id = cur.lastrowid
                                
                                
                images = item.get("image_urls", []) 
                                
                if images and current_dog_id:
                    image_data = [(current_dog_id, img_url) for img_url in images]
                                        
                    cur.executemany("""
                        INSERT INTO images (dog_id, image_url) 
                        VALUES (?, ?)
                    """, image_data)


            except json.JSONDecodeError:
                print("Invalid JSON line in", file)
conn.commit()


for file in glob.glob("data/spa.jsonl"):
    print("Loading", file)
    with open(file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                item = json.loads(line)
                cur.execute("""
                INSERT OR IGNORE INTO dogs
                (source, name, url, species, sex, age_text, age, category, breed, matched_breed, colors, accepts_dogs, accepts_cats, accepts_children, establishment, establishment_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    "SPA",
                    item.get("name"),
                    item.get("url"),
                    item.get("species"),
                    item.get("sex"),
                    item.get("age_text"),
                    item.get("age"),
                    item.get("category"),
                    item.get("breed"),
                    item.get("matched_breed"),
                    item.get("colors"),
                    item.get("accepts_dogs"),
                    item.get("accepts_cats"),
                    item.get("accepts_children"),
                    item.get("establishment"),
                    item.get("establishment_url")
                ))

                current_dog_id = cur.lastrowid
                                            
                images = item.get("image_urls", [])
                                
                if images and current_dog_id:
                    image_data = [(current_dog_id, img_url) for img_url in images]
                                        
                    cur.executemany("""
                        INSERT INTO images (dog_id, image_url) 
                        VALUES (?, ?)
                    """, image_data)


            except json.JSONDecodeError:
                print("Invalid JSON line in", file)
conn.commit()


csv_file_path = "data/breeds.csv"
# 1. Drop the table if it exists so we can rebuild it cleanly with new columns
cur.execute("DROP TABLE IF EXISTS breeds")

# 2. Create the table with ALL columns mapped to clean SQL names
# We use REAL for averages and INTEGER for the 1-5 scales
cur.execute("""
CREATE TABLE breeds (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    breed_name TEXT UNIQUE,
    detailed_description_link TEXT,
    dog_size TEXT,
    dog_breed_group TEXT,
    height_text TEXT,
    avg_height_cm REAL,
    weight_text TEXT,
    avg_weight_kg REAL,
    life_span_text TEXT,
    avg_life_span_years REAL,
    
    -- Category: Adaptability
    adaptability INTEGER,
    adapts_well_to_apartment_living INTEGER,
    good_for_novice_owners INTEGER,
    sensitivity_level INTEGER,
    tolerates_being_alone INTEGER,
    tolerates_cold_weather INTEGER,
    tolerates_hot_weather INTEGER,
    
    -- Category: Friendliness
    all_around_friendliness INTEGER,
    affectionate_with_family INTEGER,
    kid_friendly INTEGER,
    dog_friendly INTEGER,
    friendly_toward_strangers INTEGER,
    
    -- Category: Health & Grooming
    health_and_grooming_needs INTEGER,
    amount_of_shedding INTEGER,
    drooling_potential INTEGER,
    easy_to_groom INTEGER,
    general_health INTEGER,
    potential_for_weight_gain INTEGER,
    size_score INTEGER,
    
    -- Category: Trainability
    trainability INTEGER,
    easy_to_train INTEGER,
    intelligence INTEGER,
    potential_for_mouthiness INTEGER,
    prey_drive INTEGER,
    tendency_to_bark_or_howl INTEGER,
    wanderlust_potential INTEGER,
    
    -- Category: Physical Needs
    physical_needs INTEGER,
    energy_level INTEGER,
    intensity INTEGER,
    exercise_needs INTEGER,
    potential_for_playfulness INTEGER
)
""")

print(f"Loading {csv_file_path}...")

if os.path.exists(csv_file_path):
    with open(csv_file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        # Prepare the SQL query with placeholders
        # We have 41 columns to insert (excluding ID)
        insert_sql = """
        INSERT OR IGNORE INTO breeds (
            breed_name, detailed_description_link, dog_size, dog_breed_group, 
            height_text, avg_height_cm, weight_text, avg_weight_kg, 
            life_span_text, avg_life_span_years,
            adaptability, adapts_well_to_apartment_living, good_for_novice_owners, 
            sensitivity_level, tolerates_being_alone, tolerates_cold_weather, tolerates_hot_weather,
            all_around_friendliness, affectionate_with_family, kid_friendly, 
            dog_friendly, friendly_toward_strangers,
            health_and_grooming_needs, amount_of_shedding, drooling_potential, 
            easy_to_groom, general_health, potential_for_weight_gain, size_score,
            trainability, easy_to_train, intelligence, potential_for_mouthiness, 
            prey_drive, tendency_to_bark_or_howl, wanderlust_potential,
            physical_needs, energy_level, intensity, exercise_needs, potential_for_playfulness
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """

        for row in reader:
            try:
                # Map CSV keys to the values tuple
                # We use .get(key, None) to handle missing values gracefully
                values = (
                    row.get("Breed Name"),
                    row.get("Detailed Description Link"),
                    row.get("Dog Size"),
                    row.get("Dog Breed Group"),
                    row.get("Height"),
                    row.get("Avg. Height, cm"),
                    row.get("Weight"),
                    row.get("Avg. Weight, kg"),
                    row.get("Life Span"),
                    row.get("Avg. Life Span, years"),
                    
                    row.get("Adaptability"),
                    row.get("Adapts Well To Apartment Living"),
                    row.get("Good For Novice Owners"),
                    row.get("Sensitivity Level"),
                    row.get("Tolerates Being Alone"),
                    row.get("Tolerates Cold Weather"),
                    row.get("Tolerates Hot Weather"),
                    
                    row.get("All Around Friendliness"),
                    row.get("Affectionate With Family"),
                    row.get("Kid-Friendly"),
                    row.get("Dog Friendly"),
                    row.get("Friendly Toward Strangers"),
                    
                    row.get("Health And Grooming Needs"),
                    row.get("Amount Of Shedding"),
                    row.get("Drooling Potential"),
                    row.get("Easy To Groom"),
                    row.get("General Health"),
                    row.get("Potential For Weight Gain"),
                    row.get("Size"),
                    
                    row.get("Trainability"),
                    row.get("Easy To Train"),
                    row.get("Intelligence"),
                    row.get("Potential For Mouthiness"),
                    row.get("Prey Drive"),
                    row.get("Tendency To Bark Or Howl"),
                    row.get("Wanderlust Potential"),
                    
                    row.get("Physical Needs"),
                    row.get("Energy Level"),
                    row.get("Intensity"),
                    row.get("Exercise Needs"),
                    row.get("Potential For Playfulness")
                )
                
                cur.execute(insert_sql, values)
                
            except sqlite3.Error as e:
                print(f"Error inserting {row.get('Breed Name', 'Unknown')}: {e}")

    conn.commit()
    print("Breeds imported successfully with all columns.")
else:
    print(f"File not found: {csv_file_path}")


conn.close()
print("Database rebuilt successfully.")