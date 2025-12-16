def load_french_dictionary(filepath):
    """
    Loads a text file with one word per line into a Python set.
    """
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            # logic: Read line -> strip whitespace -> lowercase -> add to set
            # The 'if line.strip()' part ensures we skip empty lines
            vocab_set = {line.strip().lower() for line in f if line.strip()}
            
        print(f"✅ Loaded {len(vocab_set)} words.")
        return vocab_set
        
    except FileNotFoundError:
        print(f"❌ Error: File {filepath} not found.")
        return set()
    except UnicodeDecodeError:
        print("❌ Encoding Error: Try changing 'utf-8' to 'latin-1' or 'cp1252'")
        return set()

# Usage
french_dict = load_french_dictionary("data/french_dictionary.txt")




import re
import html

def clean_dog_name_final(raw_text, dictionary_set):
    if not raw_text or not isinstance(raw_text, str):
        return None

    # --- STEP 1: Unescape HTML ---
    # Converts &rsquo; to ’, &nbsp; to space, etc.
    text = html.unescape(raw_text)

    # --- STEP 2: Remove punctuation/residuals ---
    # We use the regex discussed previously to "stop" at the first invalid character 
    # (numbers, commas, emojis), effectively removing them.
    # We keep only: Letters, Spaces, Hyphens (-), Apostrophes (' or ’)
    pattern = r"^([^\W\d_]|[\s\-'’])+"
    match = re.match(pattern, text)
    
    if not match:
        return None
        
    cleaned_name = match.group(0).strip()
    
    # Split into words to analyze them
    # We strip extra punctuation from edges of words for the dictionary check
    tokens = cleaned_name.split()
    
    if not tokens:
        return None

    # --- STEP 3: Identify French Words ---
    # We classify every word in the name as "French" or "Not French"
    # We create a list of booleans: [True, False, True] etc.
    
    is_french_word = []
    for token in tokens:
        # Normalize: Lowercase and strip hyphen/apostrophe for the look-up
        # e.g. "Jean-Pierre" -> checks "jean", "pierre" separately usually, 
        # but here we check tokens. If token is "Jean-Pierre", we might check "jean-pierre".
        # For robustness, we check the lowercased token.
        token_clean = token.lower().strip("-'’")
        
        # Check if in dictionary
        is_french_word.append(token_clean in dictionary_set)

    # --- STEP 4 & 5: Filtering Logic ---
    
    # Check if ALL words are French (e.g. "Petit Prince", "Belle", "Princesse")
    if all(is_french_word):
        # Step 5: Output as is
        return cleaned_name.title()
    else:
        # Step 4: Not all are French (e.g. "Adorable Thor")
        # Keep ONLY the words that are NOT French
        final_tokens = []
        for word, is_french in zip(tokens, is_french_word):
            if not is_french:
                final_tokens.append(word)
                
        return " ".join(final_tokens).title()

# --- DEMONSTRATION ---

# 1. Mocking the loaded set from your file


# 2. Test Cases
examples = [
    "ELLIOT, mâle croisé",          # "Elliot" (Not French) -> Keep "Elliot"
    "Adorable Thor",                # "Adorable"(Fr), "Thor"(Not) -> Keep "Thor"
    "Petit Prince",                 # "Petit"(Fr), "Prince"(Fr) -> ALL French -> Keep "Petit Prince"
    "Princesse",                    # "Princesse"(Fr) -> ALL French -> Keep "Princesse"
    "La Belle Suzie",               # "La"(Fr), "Belle"(Fr), "Suzie"(Not) -> Keep "Suzie"
    "L'Ours",                       # "L'Ours" -> "L'"(Fr?), "Ours"(Fr) -> Likely keeps "L'Ours" or cleans it depending on tokenization
    "Rex le chien",                 # "Rex"(Not), "le"(Fr), "chien"(Fr) -> Keep "Rex"
]

print(f"{'INPUT':<30} | {'OUTPUT'}")
print("-" * 50)

for ex in examples:
    res = clean_dog_name_final(ex, french_dict)
    print(f"{ex:<30} | {res}")