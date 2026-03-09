import csv
import random
import string
from faker import Faker

def generate_dataset(n, filename):
    fake = Faker("fr_FR")
    with open(filename, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["name", "sex", "email", "phone", "address", "country", "nationality"])

        for i in range(n):
            name = fake.name()
            sex = random.choice(["male", "female"])
            email = fake.email()
            phone = fake.phone_number()
            address = fake.address()
            country = fake.country()
            nationality = country
            writer.writerow([name, sex, email, phone, address, country, nationality])

generate_dataset(100, "clients_100.csv")
generate_dataset(1000, "clients_1000.csv")
generate_dataset(10000, "clients_10000.csv")

# Code à ajouter dans le shell pour importé un certain nombre de client

""" # Importation des bibliothèques nécessaires
import csv
import time

# Début du temps d'exécution
start = time.time()

# Compteur des clients importés
count = 0

# Ouverture du fichier CSV
with open('datacsv/clients_100.csv') as file:
    # Lecture du fichier CSV
    reader = csv.DictReader(file)

    # Boucle sur chaque ligne du fichier CSV
    for row in reader:
        try:
            # Début d'une transaction
            with env.cr.savepoint():
                # Récupération des informations du client
                name = row.get('name')
                phone = row.get('phone')
                email = row.get('email')
                sex = row.get('sex')
                address = row.get('address', '').replace('\n', ' ').strip()
                country = row.get('country')
                nationality = row.get('nationality')

                # Création du partner
                partner = env['res.partner'].create({
                    'name': name,
                    'phone': phone,
                    'email': email,
                    'street': address,
                    'active': True,
                    'customer_rank': 1,
                })

                # Création du client
                env['insurance.security.clients'].create({
                    'name': name,
                    'related_partner': partner.id,
                    'sex': sex,
                    'email': email,
                    'phone': phone,
                    'adress': address,
                    'country': country,
                    'nationality': nationality,
                })

                # Incrémentation du compteur
                count += 1

        except Exception as e:
            # Annulation de la transaction en cas d'erreur
            env.cr.rollback()
            print("Erreur ligne :", row)
            print("Erreur :", e)


# Fin du temps d'exécution
end = time.time()

# Calcul du temps d'exécution
execution_time = (end - start) * 1000

# Affichage des résultats
print("Clients importés :", count)
print("Temps d'exécution (ms):", execution_time)
 """
# Code à ajouter pour lire un certains nombre de clients
""" import time

start = time.time()

clients = env['insurance.security.clients'].search([], limit=1000)

data = []
for c in clients:
    data.append({
        "name": c.name,
        "phone": c.phone,
        "email": c.email
    })

end = time.time()

execution_time = (end - start) * 1000

print("Nombre de clients lus :", len(data))
print("Temps d'exécution (ms) :", execution_time)
 """