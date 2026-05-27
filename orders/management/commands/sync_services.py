# orders/management/commands/sync_services.py
from django.core.management.base import BaseCommand
from orders.utils import sync_jap_services

class Command(BaseCommand):
    help = 'Updates service prices and availability from JAP API'

    def handle(self, *args, **kwargs):
        self.stdout.write("Starting JAP sync...")
        result = sync_jap_services()
        self.stdout.write(self.style.SUCCESS(result))