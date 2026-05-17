from django.core.management.base import BaseCommand
from core.models import Role

class Command(BaseCommand):
    help = 'Create default roles for BizSmart'

    def handle(self, *args, **options):
        roles = [
            {'name': 'owner', 'description': 'Business owner with full access'},
            {'name': 'general_manager', 'description': 'Manages daily operations'},
            {'name': 'accountant', 'description': 'Handles finances and payroll'},
            {'name': 'inventory_manager', 'description': 'Manages stock and suppliers'},
            {'name': 'cashier', 'description': 'Processes sales and serves customers'},
            {'name': 'auditor', 'description': 'Read-only access for external auditors'},
        ]
        
        for role in roles:
            obj, created = Role.objects.get_or_create(
                name=role['name'],
                defaults={'description': role['description']}
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'✅ Role "{role["name"]}" created'))
            else:
                self.stdout.write(f'⏭️  Role "{role["name"]}" already exists')
        
        self.stdout.write(self.style.SUCCESS('\n🎉 All roles created successfully!'))