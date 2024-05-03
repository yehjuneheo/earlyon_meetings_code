import csv
import os
import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "startup.settings")
django.setup()

from myapp.models import Universities

def import_universities(csv_filename):
    with open(csv_filename, mode='r', encoding='utf-8') as file:  # Specify the encoding here
        reader = csv.reader(file)
        for row in reader:
            _, created = Universities.objects.get_or_create(name=row[0])
            if created:
                print(f'Added: {row[0]}')

if __name__ == "__main__":
    csv_filename = 'university_names.csv'
    import_universities(csv_filename)
