import json
from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist

from builder.models import Domain

class Command(BaseCommand):
    help = 'Load domain metadata from a JSON file'

    def add_arguments(self, parser):
        parser.add_argument('json_file', type=str)
       
    def handle(self, *args, **kwargs):
        json_file = kwargs['json_file']
        
        with open(json_file, 'r') as file:
            data = json.load(file)

        for item in data:
            obj, created = Domain.objects.get_or_create(
                code=item['code'],
                defaults={
                    'name': item['name'],
                    'description': item.get('description', '')
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created domain: {obj.code}"))
            else:
                self.stdout.write(f"Domain already exists: {obj.code}")
