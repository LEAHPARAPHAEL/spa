## Introduction

This project aims at collecting and merging dog adoption records from two famous French shelters, 
named Seconde Chance and SPA. 

The first section of this file details how to use our project, without getting into the
implementation details. If you are interested into the details of our code, the following sections
present some of the most important aspects.


## Prequisites 

To use our project, you will need to :

1. Install the requirements.txt file using :

    pip install -r requirements.txt

2. Navigate into the shelters directory : 

    cd shelters


## Testing the crawlers

To crawl the two shelters, you can use the following commands :

1. Seconde Chance :

    scrapy scrawl secondeChance

2. SPA:

    python spa.py

Because of the cache mechanism described in the section "Storing the dogs records", it is likely
that many of the pages will be skipped, depending if a lot of time has elapsed since the last crawl.
The resulting records will be stored in the files data/seconde_chance.jsonl data/and spa.jsonl, as well as in
the database data/shelters.db.


## Updating the jsonl files

Because dogs are being continuously adopted, our database and jsonl files do not remain up to date on their own. So, 
in order to refresh the list of dogs being listed for adoption, you can run the following command :

    python manage_json.py -u -r

Where -u indicates that the URLs in the jsonl need to be checked to ensure that a dog is still listed for adoption,
and -r indicates that the updated jsonl files must replace the old ones in place (otherwise, they are created as copies in
seconde_chance_clean.jsonl and spa_clean.jsonl).

Warning : checking if a dog is still listed for adoption essentially requires another crawl pass, because we need to
check the validity of the URLs, so it can take between 4 and 5 hours to complete the two shelters.

This method allows us to update our records, while still keeping track of the dogs who have been adopted, which can be useful to 
develop statistics on adoption.


## Updating the database

If the files seconde_chance.jsonl and spa.jsonl have been updated (either to check adoption status or because some fields have
been modified), one can rebuild the database by calling :

    python build_db_from_json.py

Which is extremely fast and rebuilds the entire database from the two jsonl files seconde_chance.jsonl and spa.jsonl.


## Navigating the database using the GUI

To navigate the database without having to write manual SQL queries, one can call :

    python gui.py

Which opens a Graphical User Interface to explore the shelters.db database. This serves as an example to show how our work
could be used in practice. 
On the left side is a filter panel, which contains multiple options, including searching for a specific dog name,
breed, selecting the sex...

On the right side is a panel containing a list of dogs matching the desired criteria. When clicking on a row,
this panel is replaced by another one, containing the dog's record. If there is more than one image for this dog,
the rest can be seen using the button "see photos" below the image. If the breed of the dog has been recognized as a breed
from the dataset (see Other tables for more details), details about the breed can be accessed using the button below the breed field.


## Querying the database

Navigating this database can be done using the Graphical User Interface, as explained above. But this can
also be done using standard database querying mechanisms compatible with sqlite3.

Some examples of potential use cases for this work are illustrated in the file representation.py, which can be
called as:

    python representation.py

This queries some statistics about dogs from the database using pandas, and saves the figures in the plots/ 
directory.

Using these plots, we made a simple html page (plots/shelter_dogs.html) analysing the typical profile of dogs listed for 
adoptions, to try to investigate why their owners abandon them.


## General implementation scheme

The first part of the work consisted in retrieving the records, which was done through scraping.
However, the two websites cannot be scraped in the same way. 

1. Seconde Chance has a pure HTML website, which means we can use a standard scraping engine 
like scrapy to collect the data. This part of the work is implemented in shelters/spiders/seconde_chance.py.
Once the HTML file is downloaded, we use XPATH selectors to retrieve information about the dog. 

2. SPA has a JavaScript backend, which prevents us from using standard crawlers like scrapy.
However, by inspecting their page, we found that they use a public JSON endpoint to dynamically
load the data. There exists one JSON file per page, each one containing URLs for a dozen of dogs.
These URLs point to one JSON file per dog, containing all its information, which is then easily parsed.

The dogs records are stored in jsonl files, and then in a sqlite3 database.


## Cleaning the data

Illustration of the type of cleaning that is done to have an homogeneous database : the name of the dog 
can contain a lot of unwanted artefacts, such as (real examples) :

    - "Adorable Thor, 3 ans"
    - "Olga de Ukraine a besoin de votre aide"

It it not easy to clean these names in a fully reliable way, however we found a good compromise between
cleaning guarantee and faithfulness. This method, dubbed clean_dog_name, proceeds in three steps:

a. Removes all the text after some non-alphabetical character, for example a comma or a serial number.
b. Matches each remaining word against words from a French dictionary, located in the data/french_dictionary.txt
file. 
c. If all the words match French words, we cannot tell apart the dog's name, so we keep the whole cleaned name.
Otherwise, we remove the French words from the name, hopefully getting rid of the appendix.

Finally, since most of the names in shelters databases are in upper case, we convert the remaining cleaned name
in title case (for example "GASTON" -> "Gaston").

The other fields are cleaned in a similar manner, albeit often more easily.


## Storing the dogs records

For both these sites, once the data has been retrieved and cleaned, we create a record containing :

- source : Seconde Chance or SPA
- name
- url
- adopted : True of False (always False when crawling, can be set to True later when updating the database)
- species : "Chien"
- sex
- age_text : 5 years 6 months
- age : 5.5
- category : "junior", "adult" or "senior"
- breed : breed conventions are not shared by the two shelters, so this is the raw breed displayed by the shelter.
- matched_breed : name of the corresponding breed in the breeds dataset, or None.
- colors
- accepts_dogs
- accepts_cats
- accepts_children
- establishment : name of the establishment
- establishment_url

These records are written in separate jsonl files, named seconde_chance.jsonl and spa.jsonl.
An important detail is that, to avoid crawling several times the same page, both these crawling implementations 
contain a cache mechanism, writing the visited urls in the cache/ directory. These records are also inserted on 
the fly in the table dogs of the data/shelters.db database, with the exact same structure as the one presented above.
The primary key is an autoincrement integer. This is implemented in the following files :

1. For Seconde Chance, since the crawler is a scrapy spider, the caching logic is implemented in middlewares.py
and the storing logic in pipelines.py.

2. For SPA, everything is implemented in the same file spa.py.


## Other tables in the shelters.db database

The shelters.db database contains two other tables : images and breeds.

1. The images table contains the URLs of the images found for each dog. When we construct the record of a dog,
the list of images, if there are any, are stored as individual records in this table, with an foreign key 
dog_id referencing the primary key of the dogs table. 

2. The breeds table contains informations about the dogs breeds, obtained from this kaggle dataset :
https://www.kaggle.com/datasets/yonkotoshiro/dogs-breeds?resource=download&select=dogs_cleaned.csv

There are a lot of fields, and especially a large majority having score values between 0 and 5, which
can be practical to build some statistics. 
It also possesses an attribute breed_name, which is unique. 

For every different breed name in the SPA and Seconde Chance database, we tried to match these names to an existing
breed name from this dataset, using a combination of fuzzy matching, translation, generative AI, and manual review.
This mapping is available in the file data/breeds_mapping.json, and is used when building a dog's record to 
obtain the field "matched_breed", which is either a breed name from the dataset, or the null pointer.


## Update the jsonl files

Since crawling the two shelters while respecting the download delay can take a lot of time, we needed a robust
way to be able to update the records if we decided to change some implementation detail about information retrieval.
For example, we tried multiple ways to clean the names of the dogs, before arriving at the implementation we detailed
above. 

Instead of rerunning the entire crawl just to rename the dogs, we used the file manage_json.py, which iterates through the 
records in seconde_chance.jsonl and spa.jsonl, cleans them and copies the outputs in different files 
seconde_chance_clean.jsonl and spa_clean.jsonl. Writing in a different file is a nice safety net to not lose our
original data if the cleaning technique is not working properly. However, this can be overriden by the command line
argument -r, which replaces the original file with the new ones. This is useful ONLY is we know that the method is working
properly.

Later, we also decided to include the functionality of updating the adoption status of the dogs, and we were able to do so
using the exact same function. By passing the argument -u, we tell the method to check, for each line, if the URL is still
valid. If it is not, the dog has been adopted, and we update its adoption status. 


## Update the database

If the jsonl files have been modified out of the crawlers' scopes, the database has likely not been updated, so 
the file build_database_from_json.py is used to rebuild a database up to date with the data in the jsonl files.


## Using the database for statistical purposes

In the file reprsentation.py, we use pandas to query the database to illustrate potential usecases of our work,
by plotting a few indicators about dogs from the two shelters.
The resulting figures can be found in the plots/ directory.


## Graphical User Interface (GUI)

We built a simple GUI to navigate the database, which can be found in gui.py. Because this part of the work was not
our main focus, we took the liberty of using a LLM (Gemini) to help us write this interface. 


## Future work

Despite our best efforts to provide a good and unified database for the two shelters, our codebase is far from
perfect. We identify below two main improvements we could consider, further working on this project :

1. When updating the jsonl file, instead of only checking the validity of the URL, we could also update the age of the
dog. 

2. Another important thing to do would be to automate the process, for example by scheduling regular updates.