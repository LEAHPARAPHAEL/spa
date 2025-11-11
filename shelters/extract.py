import csv


breed_names = []

with open("data/breeds.csv", newline="", encoding="utf-8") as csvfile:
    reader = csv.reader(csvfile)
    next(reader)  # skip header
    for row in reader:
        breed_names.append(row[0])  # first column

print(breed_names)