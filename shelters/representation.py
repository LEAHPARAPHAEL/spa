import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

connect = sqlite3.connect("data/shelters.db")

# We create a DataFrame for each table
dogs_df = pd.read_sql_query("SELECT * FROM dogs", connect)
images_df = pd.read_sql_query("SELECT * FROM images", connect)
breeds_df = pd.read_sql_query("SELECT * FROM breeds", connect)

connect.close()

# We can estimate various information about our scraped data

# Number of dogs of each breeds in the shelters
top20_breeds = dogs_df['matched_breed'].value_counts()[:20]
print(top20_breeds)

# Write the percentage only on parts with more than 3%
def autopct_filter(pct):
    return f"{pct:.1f}%" if pct > 3 else ""

# Plot it as a diagram and save it in directory plots
plt.figure(figsize = (8,6))
plt.pie(top20_breeds.values, labels=top20_breeds.index, autopct=autopct_filter)
plt.title('Top 20 breeds in shelters in France in 2026.')
plt.tight_layout()
plt.savefig('plots/top20_breeds.png')
plt.show()


# Affectionate with family index in function of the number of dogs in the shelters
count_breeds = dogs_df['matched_breed'].value_counts().reset_index()
count_breeds.columns = ['breed_name', 'count']
join_dogs_breeds_df = pd.merge(count_breeds, breeds_df, left_on='breed_name', right_on='breed_name')

# We want to put in red the top20 breeds in shelter
join_dogs_breeds_df['color'] = join_dogs_breeds_df['breed_name'].apply(lambda x: 'red' if x in top20_breeds.index else 'gray')

# Plot it as a scatter plot and save it in directory plots
plt.figure(figsize = (8,6))
plt.scatter(join_dogs_breeds_df["affectionate_with_family"], join_dogs_breeds_df["count"], marker='o', c=join_dogs_breeds_df['color'], label="Breed in top20", zorder=3)
plt.title("Affectionate with family index in function of the number of each breed in the shelters.")
plt.ylabel("Number of breed dogs in the shelter")
plt.xlabel("Affectionate with family index")
plt.legend()
plt.grid(True, zorder=0)
plt.tight_layout()
plt.savefig('plots/affectionate_top20.png')
plt.show()

# Even easy to train dogs are in shelters
education_df = join_dogs_breeds_df.groupby("easy_to_train")["count"].sum().reset_index()

# Plot it as a histogram and save it in directory plots
plt.figure(figsize=(8,6))
plt.bar(education_df["easy_to_train"], education_df["count"], zorder=3)
plt.title("Number of dogs per easy to train index in shelters")
plt.xlabel("Easy to train index")
plt.ylabel("Number of dogs in shelters")
plt.grid(True, zorder=0)
plt.tight_layout()
plt.savefig("plots/easy_to_train_hist.png")
plt.show()

# In general the problem is dog size
size_df = join_dogs_breeds_df.groupby("dog_size")["count"].sum().reset_index()

# Plot it as a histogram and save it in directory plots
plt.figure(figsize=(8,6))
plt.bar(size_df["dog_size"], size_df["count"], zorder=3)
plt.xlabel("Dog size")
plt.ylabel("Number of dogs in shelters")
plt.title("Number of dogs per size in shelters")
plt.grid(True, zorder=0)
plt.tight_layout()
plt.savefig("plots/size_hist.png")
plt.show()






