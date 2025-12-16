import csv


breed_names = []

with open("data/breeds.csv", newline="", encoding="utf-8") as csvfile:
    reader = csv.reader(csvfile)
    next(reader) 
    for row in reader:
        breed_names.append(row[0] + '\n')

print(breed_names)

with open("data/reference_breeds.txt", "w") as f:
    f.writelines(breed_names)